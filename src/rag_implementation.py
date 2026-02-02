from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
# Embeddings & Chat Model
# (Now live in the dedicated langchain_openai package)
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import langchain
from langchain_classic.embeddings import CacheBackedEmbeddings

# Vector Store
# (Lives in langchain_community)
from langchain_community.vectorstores import FAISS

# Prompts
# (ChatPromptTemplate is preferred over PromptTemplate for Chat Models)
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
# 5. Chains
#from langchain_classic.chains import create_retrieval_chain
#from langchain_classic.chains.combine_documents import create_stuff_documents_chain
#from langchain_core.documents import Document

# Logging and OpenAI configuration and logging
from rich.logging import RichHandler
from dotenv import load_dotenv
from openai import RateLimitError
import logging

langchain.debug = True

# OS
import os

# Configure basic config with RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s", # Rich handles the timestamp and level separately
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("rag")

# load the env variables
load_dotenv(dotenv_path=".env")

def clean_filename(name: str):
    import re
    name = name.replace(".pdf", "")
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)

def get_rag_chain(resume_text, resume_file_name):


    # Initialize the OpenAI Embeddings model with API credentials
    embeddings = OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY"),  # OpenAI API key for authentication
        chunk_size=10,
        max_retries=5
    )

    ## Vector DB Persistence
    out_dir = 'vector_db'  # name of the vector database
    ## Check if the Vector Store exist
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    # Defining index file name
    db_index_file_name = f"index_{clean_filename(resume_file_name)}"
    # Defining faiss path
    db_faiss_path = f"{out_dir}/{db_index_file_name}.faiss"
    logger.info("ℹ️ Checking for Vector Store ")
    if os.path.exists(db_faiss_path):
        logger.info("ℹ️ Existing vector store found.")
        # Load existing
        vectorstore_local = FAISS.load_local(
            folder_path=out_dir,
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
            index_name=f"{db_index_file_name}"
        )
    else:
        logger.warning("⚠️ No vector store found ..")
        # 1. Split the text into chunks
        logger.info("ℹ️ Split text into chunks")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=100)
        chunks = text_splitter.split_text(resume_text)

        try:
            # 2. Creating Embeddings
            logger.info("ℹ️ Creating Embeddings .")
            vectorstore_local = FAISS.from_texts(chunks, embedding=embeddings)
        except RateLimitError as e:
            logging.exception("[🚨] Rate limit hit!")
            logging.error(e)
            raise

        logger.info("[ ℹ️ ] Storing Vector Store for Caching ..")
        vectorstore_local.save_local(folder_path=out_dir, index_name=db_index_file_name)

    # 3. Setup the Retriever
    # We will retrieve the top 3 most relevant chunks of the resume
    retriever = vectorstore_local.as_retriever(search_type="similarity", search_kwargs={"k": 3})

    # 4. Define the Prompt
    # This tells the LLM how to behave
    # 4. Define the Prompt (Tuned)
    prompt_template = """
        You are a Senior Technical Recruiter with 20 years of experience. 
        You are strict, analytical, and detail-oriented.

        Your goal is to analyze the Candidate's Resume against the Job Description.

        Context (Resume segments): {context}

        User Query: {question}

        Your task are the following:
        1-Answer the query using ONLY the information provided in the context. 
        If the information is not in the resume, explicitly state "Not mentioned in resume" rather than guessing.
        2- Fairly Analyze and Interpret the candidate resume based on the job description and provide a professional assessment.
        """

    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    # 5. Create the Chain
    llm = ChatOpenAI(model="gpt-4o", temperature=0)  # Use gpt-4 or gpt-3.5-turbo

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    return qa_chain