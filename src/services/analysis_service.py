from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import RateLimitError

from prompts.prompts import get_prompt_ver, jd_as_context, prompt_template_recruiter
from utils.parsing import extract_json_object, extract_match_score

logger = logging.getLogger("analysis_service")

load_dotenv()


VECTOR_DB_DIR = Path("vector_db")


def clean_filename(name: str) -> str:
    """
    Create a filesystem-safe name for cached vector store files.
    """
    import re

    name = name.replace(".pdf", "")
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def build_rag_chain(resume_text: str, resume_file_name: str) -> RetrievalQA:
    """
    Build or load a FAISS-backed retrieval QA chain for a resume.
    """
    embeddings = OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY"),
        chunk_size=10,
        max_retries=5,
    )

    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

    db_index_file_name = f"index_{clean_filename(resume_file_name)}"
    db_faiss_path = VECTOR_DB_DIR / f"{db_index_file_name}.faiss"

    logger.info("Checking for vector store at %s", db_faiss_path)

    if db_faiss_path.exists():
        logger.info("Existing vector store found: %s", db_faiss_path)
        vectorstore_local = FAISS.load_local(
            folder_path=str(VECTOR_DB_DIR),
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
            index_name=db_index_file_name,
        )
    else:
        logger.warning("No vector store found. Building a new one.")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=100)
        chunks = text_splitter.split_text(resume_text)

        try:
            vectorstore_local = FAISS.from_texts(chunks, embedding=embeddings)
        except RateLimitError:
            logger.exception("Rate limit hit while creating embeddings")
            raise

        vectorstore_local.save_local(
            folder_path=str(VECTOR_DB_DIR),
            index_name=db_index_file_name,
        )

    retriever = vectorstore_local.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3},
    )

    prompt = PromptTemplate(
        template=prompt_template_recruiter,
        input_variables=["context", "question"],
    )

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def extract_job_metadata(qa_chain: RetrievalQA, job_description: str, rag_run_config: dict | None = None) -> dict[str, str]:
    """
    Extract company and title metadata from the job description.
    """
    questions = get_prompt_ver("v2")
    if not questions:
        return {"company": "", "title": ""}

    query = jd_as_context(job_description)
    response = qa_chain.invoke(
        {"query": f"{query}\n\n{questions['q_meta']}"},
        config=rag_run_config or {},
    )

    raw_text = response.get("result", "")
    data = extract_json_object(raw_text)

    if not data:
        return {"company": "", "title": ""}

    return {
        "company": str(data.get("company", "Unknown")),
        "title": str(data.get("title", "Unknown")),
    }


def run_candidate_analysis(
    resume_text: str,
    resume_file_name: str,
    job_description: str,
    rag_run_config: dict | None = None,
) -> dict:
    """
    Run the full analysis workflow and return structured results.
    """
    qa_chain = build_rag_chain(resume_text, resume_file_name)
    questions = get_prompt_ver("v2") or {}
    query = jd_as_context(job_description)

    results: dict = {}

    metadata = extract_job_metadata(qa_chain, job_description, rag_run_config)
    results["company"] = metadata.get("company", "")
    results["title"] = metadata.get("title", "")

    q3_ans = qa_chain.invoke(
        {"query": f"{query}\n\n{questions.get('q3', '')}"},
        config=rag_run_config or {},
    )
    results["score"] = extract_match_score(q3_ans["result"])

    for key in ["q1", "q2", "q4", "q5", "q6", "q7", "q8", "q9"]:
        ans = qa_chain.invoke(
            {"query": f"{query}\n\n{questions.get(key, '')}"},
            config=rag_run_config or {},
        )
        results[key] = ans["result"]

    results["report"] = build_analysis_report(job_description, results)
    return results


def build_analysis_report(job_description: str, results: dict) -> str:
    """
    Build a markdown report from analysis results.
    """
    report = "# Candidate Analysis Report\n"
    report += f"**Job Description:** {job_description}\n\n---\n\n"
    report += f"## Match Score: {results.get('score', 0)}%\n\n"
    report += f"### Skills Check\n{results.get('q1', '')}\n\n"
    report += f"### Fit Conclusion\n{results.get('q2', '')}\n\n"
    report += f"### Strengths\n{results.get('q4', '')}\n\n"
    report += f"### Opportunities\n{results.get('q5', '')}\n\n"
    report += f"### Red Flags\n{results.get('q6', '')}\n\n"
    report += f"### Cover Letter\n{results.get('q7', '')}\n\n"
    report += f"### Differentiators\n{results.get('q8', '')}\n\n"
    report += f"### Elevator Pitch\n{results.get('q9', '')}\n\n"
    return report