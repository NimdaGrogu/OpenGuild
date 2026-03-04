# Libraries
from streamlit_option_menu  import option_menu
from ingestion import get_jd_with_playwright, get_pdf_text_pdfplumber
from prompt_eng_recruiter import get_prompt_ver, jd_as_context
from rag_implementation import get_rag_chain
from helper import extract_match_score, DebugCallbackHandler, load_tracker_data, save_tracker_data
from css_template import sidebar_footer_style
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
import os, json, re
import logging
import pandas as pd
from rich.logging import RichHandler


# Configure basic Logging config with RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("app")

# load the env variables
load_dotenv()
open_api_key = os.getenv("OPENAI_API_KEY")

# --- Streamlit Configuration
st.set_page_config(page_title="AI Job Hunt Assistant", page_icon="🚀", layout='wide')

def main():
    # 1. Set up the sidebar
    with st.sidebar:
        st.title("👔 AI Job Hunt Assistant")
        selected = option_menu(
            menu_title="Main Menu",
            options=["Recruiter Assistance","Job Tracker", ], # Required
            icons=["robot","clipboard-data"],  # Optional (Bootstrap icons)
            menu_icon="cast",  # Optional
            default_index=0,  # Optional

        )
    # 2. Logic to Switch Between "Pages"
    if selected == "Recruiter Assistance":
        ai_job_hunt()
    elif selected == "Job Tracker":
        job_tracker()


# Placeholder functions for your features
def ai_job_hunt():
    # Main Streamlit
    st.title(" 🧠 Candidate Assistant tool")
    st.markdown("**Provide a job description URL and a candidate resume to get a comprehensive analysis.**")

    # ---- Sidebar for Inputs
    with st.sidebar:
        st.markdown("---")  # Optional horizontal rule
        st.header("Input Data")
        # Input 1: Web Page Link (Job Description)
        jd_url = st.text_input(placeholder="https://linkedin.com/jobs/",
                               max_chars=5000,
                               label="Job Description URL ")
        # Input 2: Raw text (Job Description)
        # jd_text = st.text_input("Job Description Raw Text", max_chars=5000)
        jd_text = st.text_input("Job Description Raw Text")
        # Input 3: Upload the PDF
        uploaded_resume = st.file_uploader("Upload Candidate Resume (PDF)", type=["pdf"])
        # Button to trigger analysis
        submit = st.button("Analyse Candidate Resume")

        # --- Reset Button ---
        if st.button("Reset Analysis"):
            # Clear the specific session state keys
            if 'analysis_results' in st.session_state:
                del st.session_state['analysis_results']
            if 'full_report' in st.session_state:
                del st.session_state['full_report']

            os.environ.pop("VERBOSE_RAG_LOGS", None)
            # Force the app to rerun immediately
            st.rerun()
        # -------------------------

        # 4. Add your footer content (LAST thing in the sidebar)
        st.markdown("---")  # Optional horizontal rule
        st.link_button("Visit GitHub Repo", "https://github.com/NimdaGrogu/job-hunt-assistant.git")
        st.caption("© 2026 Grogus")

        # 3. Inject the CSS
        st.markdown(sidebar_footer_style, unsafe_allow_html=True)

    # --- MAIN SECTION ---

    # 1. Initialize Session State
    # A place to store the data so it survives when the clicked 'Download' is true
    if 'analysis_results' not in st.session_state:
        st.session_state['analysis_results'] = None
    if 'full_report' not in st.session_state:
        st.session_state['full_report'] = None
    # Initialize History
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    # --- Submit Button ---

    # 2. Trigger Analysis (COMPUTATION LAYER)
    if submit:
        # --- Validations ---
        if not open_api_key:
            st.error("⚠️ OpenAI API Key is missing. Please check your .env file.")
            st.stop()
        if not uploaded_resume:
            st.warning("⚠️ Please provide Resume PDF ...")
            st.stop()
        if not jd_url and not jd_text:
            st.error("⚠️ Please provide Job Description ...")
            st.stop()

        # --- Job Description Validation ---
        if jd_url:
            job_description = get_jd_with_playwright(jd_url)
            if job_description is None:
                st.error("❌ Something went wrong accessing the URL.")
                st.stop()
        else:
            job_description = jd_text

        # Get Resume Text
        with st.spinner("Extracting text from Resume..."):
            try:
                # resume_text = get_pdf_text_pymupdf(uploaded_file=uploaded_resume)
                resume_text = get_pdf_text_pdfplumber(uploaded_resume)
            except Exception as e:
                st.error(f"☠️ An error occurred reading the PDF: {uploaded_resume}")
                st.stop()

        # --- MAIN ANALYSIS LOOP WITH PROGRESS BAR ---
        if resume_text and job_description:
            try:
                # 1. Setup Phase
                # Initialize the progress bar
                progress_bar = st.progress(1, text="Initializing AI 🧠 ..")
                # 2. Define the RAG Run Config dynamically
                rag_run_config = {}
                enable_verbose = os.getenv("VERBOSE_RAG_LOGS", "false")
                if enable_verbose == 'True' or enable_verbose == 'true':
                    logger.info("🔧 Verbose RAG Logging is ENABLED")
                    debug_handler = DebugCallbackHandler()
                    # Pass the handler if enabled
                    rag_run_config = {"callbacks": [debug_handler]}
                else:
                    logger.info("🔧 Verbose RAG Logging is DISABLED")
                    # Empty config means no extra callbacks
                    rag_run_config = {}

                # Defining the RAG Chain
                qa_chain = get_rag_chain(resume_text, uploaded_resume.name)
                # Extracting the prompts to use
                questions = get_prompt_ver(version="v2")
                # Combining the Job Description as a context in base query
                query = jd_as_context(jd=job_description)

                # Storing the RESULTS
                results = {}

                #### Tracker integration
                # 1.5 Extract Metadata (Company & Title)
                progress_bar.progress(5, text="Extracting Job Metadata... (5%)")
                try:

                    meta_ans = qa_chain.invoke(
                        {"query": f"{query}\n\n{questions['q_meta']}"},
                        config=rag_run_config
                    )

                    raw_text = meta_ans['result']

                    # 1. Find the exact JSON brackets (ignores "Here is the JSON:" text)
                    match = re.search(r'\{.*}', raw_text, re.DOTALL)
                    clean_json_string = "None"
                    if match:
                        clean_json_string = match.group(0)

                        # CLEANUP: Remove hidden web characters and newlines that break JSON
                        clean_json_string = clean_json_string.replace('\xa0', ' ').replace('\n', ' ').strip()

                        #  Parse with strict=False so Python ignores minor control character issues
                        job_meta = json.loads(clean_json_string, strict=False)

                        # Save to results
                        results['company'] = job_meta.get('company', 'Unknown')
                        results['title'] = job_meta.get('title', 'Unknown')
                        logger.info(f"ℹ️  Extracted: {results['title']} at {results['company']}")
                    else:
                        logger.warning(f"⚠️ No JSON brackets found. Raw output: {raw_text}")
                        results['company'] = ""
                        results['title'] = ""

                except Exception as e:
                    # If it still fails, it prints exactly why so we can debug it
                    logger.warning(f"⚠️ Failed to parse metadata. Error: {e} | Raw String: {clean_json_string}")
                    results['company'] = ""
                    results['title'] = ""
                #####

                # 2. Q3 Match Score (10%)
                progress_bar.progress(10, text="Calculating Match Score... (10%)")
                logger.info(f" ✅ Analysis and Assessment Start ...")

                q3_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q3']}"},
                    config=rag_run_config
                )
                results['score'] = extract_match_score(q3_ans['result'])

                # 3. Q1 Skills (20%)
                progress_bar.progress(20, text="Analyzing Skills Gap... (20%)")
                q1_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q1']}"},
                    config=rag_run_config
                )
                results['q1'] = q1_ans['result']

                # 4. Q2 Fit Check (30%)
                progress_bar.progress(30, text="Evaluating Cultural & Technical Fit... (30%)")
                q2_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q2']}"},
                    config=rag_run_config
                )
                results['q2'] = q2_ans['result']

                # 5. SWOT Analysis
                progress_bar.progress(40, text="Identifying Strengths... (40%)")
                q4_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q4']}"},
                    config=rag_run_config
                )
                results['q4'] = q4_ans['result']

                progress_bar.progress(55, text="Identifying Opportunities... (55%)")
                q5_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q5']}"},
                    config=rag_run_config
                )
                results['q5'] = q5_ans['result']

                progress_bar.progress(70, text="Checking for Red Flags... (70%)")
                q6_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q6']}"},
                    config=rag_run_config
                )
                results['q6'] = q6_ans['result']

                progress_bar.progress(80, text="Drafting Cover Letter... (80%)")
                q7_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q7']}"},
                    config=rag_run_config
                )
                results['q7'] = q7_ans['result']

                progress_bar.progress(90, text="Generating Interview Tips... (90%)")
                q8_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q8']}"},
                    config=rag_run_config
                )
                results['q8'] = q8_ans['result']

                q9_ans = qa_chain.invoke({
                    "query": f"{query}\n\n{questions['q9']}"},
                    config=rag_run_config
                )
                results['q9'] = q9_ans['result']

                # Finish
                progress_bar.progress(100, text="Analysis Complete! (100%)")
                progress_bar.empty()

                # --- BUILD REPORT & SAVE ---
                report = f"# Candidate Analysis Report\n"
                report += f"**Job Description:** {jd_url or 'Provided Text'}\n\n---\n\n"
                report += f"## Match Score: {results['score']}%\n\n"
                report += f"### Skills Check\n{results['q1']}\n\n"
                report += f"### Fit Conclusion\n{results['q2']}\n\n"
                report += f"### Strengths\n{results['q4']}\n\n"
                report += f"### Opportunities\n{results['q5']}\n\n"
                report += f"### Red Flags\n{results['q6']}\n\n"
                report += f"### Cover Letter\n{results['q7']}\n\n"
                report += f"### Differentiators\n{results['q8']}\n\n"
                report += f"### Elevator Pitch\n{results['q9']}\n\n"

                # SAVE TO SESSION STATE
                st.session_state['analysis_results'] = results
                st.session_state['full_report'] = report

                # --- SAVE TO HISTORY (Your Logic Here) ---
                # ... (Insert your history saving code here) ...

                st.success("✅ Analysis and Assessment Completed ..!")
                logger.info(f" ✅ Analysis and Assessment Completed ..!")

            except Exception as e:
                st.error(f"☠️ An error occurred: {e}")
                st.stop()

    # 3. Render Results (DISPLAY LAYER)
    # This block runs if 'analysis_results' exists in memory, regardless of button clicks.
    if st.session_state['analysis_results']:
        results = st.session_state['analysis_results']

        st.markdown("---")
        st.subheader("📊 Analysis Results")

        tabs = st.tabs(["Fit Analysis", "Strengths & Weaknesses", "Cover Letter & Tips", "Interview Tips"])

        with tabs[0]:
            st.markdown("### 🎯 Fit Assessment")

            # Display Score
            st.metric(label="Match Score:", value=f"{results['score']}%")
            st.progress(results['score'] / 100)

            if results['score'] < 50:
                st.error("Low Match - Missing critical skills.")
            elif results['score'] < 80:
                st.warning("Good Match - Some gaps identified.")
            else:
                st.success("High Match - Strong candidate!")

            with st.expander("**Skills Check:**"):
                st.write(results['q1'])

            with st.expander("**Fit Check:**"):
                st.write(results['q2'])

        with tabs[1]:
            st.markdown("### 📈 SWOT Analysis")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info("Strengths", icon="💪")
                st.write(results['q4'])
            with col2:
                st.warning("Opportunities", icon="🌤️")
                st.write(results['q5'])
            with col3:
                st.error("Weaknesses", icon="🚨")
                st.write(results['q6'])

        with tabs[2]:
            st.markdown("### 📝 Application Kit")
            with st.expander("Draft Cover Letter"):
                st.write(results['q7'])
            with st.expander("**How to Stand Out:**"):
                st.write(results['q8'])

        with tabs[3]:
            st.subheader("🎤 Interview Elevator Pitch")
            st.info(results['q9'])

        # --- EXPORT BUTTON ---
        st.divider()
        st.subheader("📥 Export Report")

        # This button will now work because 'full_report' is read from session_state
        st.download_button(
            label="Download Full Analysis Report (Markdown/Text)",
            data=st.session_state['full_report'],
            file_name="candidate_analysis.md",
            mime="text/markdown"
        )
        # Tracker Integration
        st.divider()
        st.subheader("💾 Save to Job Tracker")
        st.markdown("Add this analysis directly to your pipeline.")

        # Implementing a form so the app doesn't rerun until the user clicks "Save"
        with st.form("save_to_tracker_form"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                # Inject the extracted company name as the default value
                company_input = st.text_input("Company Name*", value=results.get('company', ''))
            with col2:
                # Inject the extracted job title as the default value
                title_input = st.text_input("Job Title*", value=results.get('title', ''))
            with col3:
                score_val = results.get('score', 0)
                st.metric("Match Score", f"{score_val}%")

            save_btn = st.form_submit_button("Save to Tracker")

            if save_btn:
                if company_input and title_input:
                    # 1. Load the existing tracker data
                    df = load_tracker_data()

                    # 2. Create the new entry
                    try:
                        new_entry = pd.DataFrame([{
                            "Date Applied": datetime.today().strftime("%Y-%m-%d"),
                            "Company": company_input,
                            "Job Title": title_input,
                            "Match Score": score_val,
                            "Status": "Applied",  # Default status
                            "URL": jd_url if jd_url else jd_text,
                            "Notes": f"AI Analysis mapped from resume: {uploaded_resume.name}"
                        }])
                    except Exception as e:
                        st.error(f"☠️ An error occurred: {e} - Data is not loaded correctly, reset the analysis and try the assessment again.. ")
                        st.stop()


                    # 3. Append and Save
                    df = pd.concat([df, new_entry], ignore_index=True)
                    save_tracker_data(df)

                    st.success(f"✅ {title_input} at {company_input} saved successfully!")
                else:
                    st.error("⚠️ Please enter both the Company Name and Job Title to save.")



def job_tracker():
    st.header("📊 Job Tracker tool")
    st.markdown("Keep track of your job applications, scores, and interview statuses.")

    # 1. Load the data
    df = load_tracker_data()

    # 2. Dashboard Metrics
    st.subheader("📈 Quick Stats")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Applied", len(df))
    col2.metric("Interviewing", len(df[df['Status'] == 'Interviewing']) if not df.empty else 0)
    col3.metric("Offers", len(df[df['Status'] == 'Offer']) if not df.empty else 0)
    col4.metric("Rejected", len(df[df['Status'] == 'Rejected']) if not df.empty else 0)

    st.markdown("---")
    st.subheader("📈 Application Insights")

    # Only show charts if there is data in the tracker
    if not df.empty:
        # Create two columns for side-by-side charts
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("**Pipeline Status**")
            # Count how many applications are in each status
            status_counts = df['Status'].value_counts()
            # Streamlit natively draws a bar chart from a Pandas Series
            st.bar_chart(status_counts)

        with chart_col2:
            st.markdown("**Application Activity Over Time**")
            # Ensure the 'Date Applied' column is treated as actual dates
            df['Date Applied'] = pd.to_datetime(df['Date Applied'])

            # Group by the date and count the number of applications per day
            timeline_counts = df.groupby(df['Date Applied'].dt.date).size()

            # Draw a line chart to show momentum
            st.line_chart(timeline_counts)
    else:
        st.info("Add some applications to see your visual insights!")

    st.markdown("---")

    # 3. Add a New Job Form
    with st.expander("➕ Add New Application", expanded=False):
        with st.form("add_job_form"):
            colA, colB = st.columns(2)
            with colA:
                new_company = st.text_input("Company Name*")
                new_title = st.text_input("Job Title*")
                new_score = st.number_input("Match Score (%)", min_value=0, max_value=100, value=0)
            with colB:
                new_status = st.selectbox("Status",
                                          ["Applied", "Screening", "Interviewing", "Offer", "Rejected", "Ghosted"])
                new_url = st.text_input("Job URL")
                new_date = st.date_input("Date Applied", datetime.today())

            new_notes = st.text_area("Notes (e.g., recruiter name, next steps)")

            submit_job = st.form_submit_button("Save Application")

            if submit_job:
                if new_company and new_title:
                    # Create a new row
                    new_row = pd.DataFrame([{
                        "Date Applied": new_date.strftime("%Y-%m-%d"),
                        "Company": new_company,
                        "Job Title": new_title,
                        "Match Score": new_score,
                        "Status": new_status,
                        "URL": new_url,
                        "Notes": new_notes
                    }])
                    # Append and save
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_tracker_data(df)
                    st.success(f"✅ Added {new_title} at {new_company}!")
                    st.rerun()  # Refresh the page to show the new data
                else:
                    st.error("⚠️ Company Name and Job Title are required.")

    # 4. Interactive Data Editor
    st.subheader("📋 Your Applications")
    if not df.empty:
        # st.data_editor allows the user to double-click and edit cells directly!
        edited_df = st.data_editor(
            df,
            width='stretch',
            num_rows="dynamic",  # Allows user to delete rows
            column_config={
                "Date Applied": st.column_config.DateColumn(
                    "Date Applied",
                    help="The day you submitted the application",
                    format="DD-MM-YYYY",
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    help="Current stage of the application",
                    options=["Applied", "Screening", "Interviewing", "Offer", "Rejected", "Ghosted"],
                    required=True,
                ),
                "Match Score": st.column_config.ProgressColumn(
                    "Match Score",
                    help="AI Fit Score",
                    format="%f%%",
                    min_value=0,
                    max_value=100,
                ),
                "URL": st.column_config.LinkColumn("Job Link")
            }
        )

        # Save changes if the user edits the table directly
        if not edited_df.equals(df):
            save_tracker_data(edited_df)
            st.success("✅ Tracker updated!")
            st.rerun()
    else:
        st.info("No applications tracked yet. Use the form above to add your first one!")

if __name__ == "__main__":
    main()
