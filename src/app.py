# Libraries

from ingestion import get_jd_from_url, get_pdf_text_pypdf, get_pdf_text_pdfplumber
from prompt_eng_recruiter import get_prompt_ver
from rag_implementation import get_rag_chain
from helper import extract_match_score
from dotenv import load_dotenv
import streamlit as st
import os
import logging
from rich.logging import RichHandler


# Configure basic Logging config with RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s", # Rich handles the timestamp and level separately
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("app")

# load the env variables
load_dotenv()
open_api_key = os.getenv("OPENAI_API_KEY")

# Streamlit Configuration
st.set_page_config(page_title="AI Job Hunt Assistant", page_icon="🚀", layout='wide')
# Main Streamlit
st.title("👔 AI Job Hunt Assistant")
st.markdown("**Provide a job description URL and a candidate resume to get a comprehensive analysis.**")
# Sidebar for Inputs
with st.sidebar:
    st.header("Input Data")
    # Input 1: Web Page Link (Job Description)
    jd_url = st.text_input(placeholder="https://linkedin.com/jobs/",
                           max_chars=5000,
                           label="Job Description URL ")
    # Input 2: Raw text (Job Description)
    jd_text = st.text_input("Job Description Raw Text", max_chars=5000)
    # Input 3: Upload the PDF
    uploaded_resume = st.file_uploader("Upload Candidate Resume (PDF)", type=["pdf"])
    # Button to trigger analysis
    submit = st.button("Analyse Candidate Resume")


    # Markdown for the badge
    sidebar_footer_style = """
    <style>
    /* This targets the specific container in the sidebar */
    [data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }

    /* This targets the last element inside the sidebar and pushes it down */
    [data-testid="stSidebar"] > div:first-child > div:last-child {
        margin-top: auto;
    }
    </style>
    """
    # 4. Add your footer content (This must be the LAST thing you write to the sidebar)
    st.markdown("---")  # Optional horizontal rule
    st.link_button("Visit GitHub Repo", "https://github.com/NimdaGrogu/job-hunt-assistant.git")
    st.caption("© 2026 Grogus")

    # 3. Inject the CSS
    st.markdown(sidebar_footer_style, unsafe_allow_html=True)

# Main Section
if submit:
    # --- Validations ---
    if not open_api_key:
        st.error("⚠️ OpenAI API Key is missing. Please check your .env file.")
        st.stop()  # Stop execution here

    if not uploaded_resume:
        st.warning("⚠️ Please provide Resume PDF ...")
        st.stop()  # Stop execution here

    if not jd_url and not jd_text:
        st.error("⚠️ Please provide Job Description ...")
        st.stop()  # Stop execution here

    # --- Processing ---
    # A. Get Job Description Text
    # Prioritize URL if provided, otherwise use text and check if the URL is not None, HTTP Errors
    if jd_url:
        job_description = get_jd_from_url(jd_url)
        if job_description is None:
            st.error("❌ Something went wrong accessing the URL provided, try again or try the raw text instead..")
            st.stop()
    else:
        job_description = jd_text


    # B. Get Resume Text
    with st.spinner("Extracting information from the resume .."):
        resume_text = get_pdf_text_pdfplumber(uploaded_resume)
        st.success("✅ Done ..")

    if resume_text and job_description:
        with st.spinner("Processing Resume and Job Description..."):
            #st.success("✅ Data successfully extracted!")

            with st.expander("View Extracted Data"):
                st.subheader("Job Description Snippet")
                st.write(job_description[:500] + "...")
                st.subheader("Resume Snippet")
                st.write(resume_text[:500] + "...")

    with st.spinner("Analysing Candidate Resume and Job Description.."):
        # 1. Build the RAG Chain with the Resume Data
        try:
            qa_chain = get_rag_chain(resume_text, uploaded_resume.name)
        except:
            st.error(f"☠️ Something went Wrong trying to process your request ..")
            st.stop()

        # 2. Define your questions
        questions = get_prompt_ver(version="v2")

        # Initialize an empty string to accumulate the report
        full_report = f"# Candidate Analysis Report\n"
        full_report += f"**Job Description:** {jd_url}\n\n"
        full_report += "---\n\n"

        # 3. Run the Analysis
        st.markdown("---")
        st.subheader("📊 Analysis Results")

        # Create tabs for a cleaner UI
        tabs = st.tabs(["Fit Analysis", "Strengths & Weaknesses", "Cover Letter & Tips", "Interview Tips"])

        # We combine the Job Description as a context in the base query
        base_query = f"Based on this Job Description: \n\n {job_description} \n\n Answer this: "

        with tabs[0]:  # Q1, Q2, Q3
            st.markdown("### 🎯 Fit Assessment")
            logger.info("ℹ️ Entering Fit Assessment")
            logger.info("ℹ️ Match Details: LLM Processing Q3")
            try:
                q3_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q3']}"})
            except:
                st.error(f"☠️ Something went Wrong trying to process your request ..")
                st.stop()
            with st.expander("**Match Details:** "):
                # Parse the number
                score = extract_match_score(q3_ans['result'])
                # Display the Progress Bar
                st.metric(label="Match Score", value=f"{score}%")
                st.progress(score / 100)
                if score < 50:
                    st.error("Low Match - Missing critical skills.")
                elif score < 80:
                    st.warning("Good Match - Some gaps identified.")
                else:
                    st.success("High Match - Strong candidate!")
                # -------------------------------
                # Add to Report
                full_report += f"## Match Score: {score}%\n\n"

            logger.info("ℹ️ Processing Skills Check LLM Processing Q1")
            q1_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q1']}"})
            with st.expander("**Skills Check:**"):
                st.write(f"{q1_ans['result']}")
                # Add to Report
                full_report += f"### Skills Check\n{q1_ans['result']}\n\n"

            logger.info("ℹ️ Processing Fit Check: LLM Processing Q2")
            q2_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q2']}"})
            with st.expander("**Fit Check:**" ):
                st.write(f"{q2_ans['result']}")
                full_report += f"### Fit Conclusion\n{q2_ans['result']}\n\n"

        with tabs[1]:  # Q4, Q5 , Q6
            st.markdown("### 📈 SWOT Analysis")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info("Strengths",icon="💪")
                ## LOGGING
                logger.info("ℹ️ Processing Candidate Strengths")
                q4_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q4']}"})
                st.write(q4_ans['result'])
                full_report += f"### Strengths\n{q4_ans['result']}\n\n"
            with col2:
                logger.info("ℹ️ Processing Candidate Opportunities")
                st.warning("Opportunities", icon="🌤️")
                q5_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q5']}"})
                st.write(q5_ans['result'])
                full_report += f"### Opportunities\n{q5_ans['result']}\n\n"
            with col3:
                st.error("Weaknesses",icon="🚨")
                logger.info("ℹ️ Processing Candidate Weaknesses")
                q6_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q6']}"})
                st.write(q6_ans['result'])
                full_report += f"### Red Flags\n{q6_ans['result']}\n\n"

        with tabs[2]:  # Q7, Q8
            st.markdown("### 📝 Application Kit")
            logger.info("ℹ️ Processing Cover Letter")
            q7_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q7']}"})
            with st.expander("Draft Cover Letter"):
                st.write(q7_ans['result'])
                full_report += f"### Red Flags\n{q6_ans['result']}\n\n"
            logger.info("ℹ️ Processing How to help the Candidate Stand Out")
            q8_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q8']}"})
            with st.expander("**How to Stand Out:**"):
                st.write(f"{q8_ans['result']}")
                full_report += f"### Differentiators\n{q8_ans['result']}\n\n"
        with tabs[3]: # Q9
            st.subheader("🎤 Interview Elevator Pitch")
            logger.info(f"ℹ️ Processing STAR Framework")
            q9_ans = qa_chain.invoke({"query": f"{base_query}\n\n{questions['q9']}"})
            st.info(f"{q9_ans['result']}")
            full_report += f"### Elevator Pitch\n{q9_ans['result']}\n\n"


        logger.info("✅ Analysis and Assessment Completed ..!")
        st.success("✅ Data successfully Processed!")
        # --- EXPORT BUTTON ---
        st.divider()
        st.subheader("📥 Export Report")
        st.download_button(
            label="Download Full Analysis (Markdown/Text)",
            data=full_report,
            file_name="candidate_analysis.md",
            mime="text/markdown")












