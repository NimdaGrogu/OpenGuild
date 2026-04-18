from __future__ import annotations

import logging
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from data.tracker_repository import load_tracker_data, save_tracker_data
from services.analysis_service import run_candidate_analysis
from utils.css_template import sidebar_footer_style

logger = logging.getLogger("candidate_coach")


def render_candidate_coach() -> None:
    """
    Render the Candidate Coach page.
    """
    if "tracker_success_msg" in st.session_state:
        st.toast(st.session_state["tracker_success_msg"], icon="✅")
        del st.session_state["tracker_success_msg"]

    st.title("🤖✨ Candidate Assistant tool")
    st.markdown(
        "**Provide a job description URL and a candidate resume to get a comprehensive analysis.**"
    )

    with st.sidebar:
        st.markdown("---")
        st.header("Input Data")

        jd_url = st.text_input(
            label="Job Description URL",
            placeholder="https://linkedin.com/jobs/",
            max_chars=5000,
        )
        jd_text = st.text_input("Job Description Raw Text")
        uploaded_resume = st.file_uploader("Upload Candidate Resume (PDF)", type=["pdf"])
        submit = st.button("Analyse Candidate Resume")

        if st.button("Reset Analysis"):
            st.session_state.pop("analysis_results", None)
            st.session_state.pop("full_report", None)
            os.environ.pop("VERBOSE_RAG_LOGS", None)
            st.rerun()

        st.markdown("---")
        st.link_button("Visit GitHub Repo", "https://github.com/NimdaGrogu/job-hunt-assistant.git")
        st.caption("© 2026 Grogus")
        st.markdown(sidebar_footer_style, unsafe_allow_html=True)

    if "analysis_results" not in st.session_state:
        st.session_state["analysis_results"] = None
    if "full_report" not in st.session_state:
        st.session_state["full_report"] = None

    if submit:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("⚠️ OpenAI API Key is missing. Please check your .env file.")
            st.stop()

        if not uploaded_resume:
            st.warning("⚠️ Please provide Resume PDF ...")
            st.stop()

        if not jd_url and not jd_text:
            st.error("⚠️ Please provide Job Description ...")
            st.stop()

        if jd_url:
            from utils.ingestion import get_jd_with_playwright

            job_description = get_jd_with_playwright(jd_url)
            if job_description is None:
                st.error("❌ Something went wrong accessing the URL.")
                st.stop()
        else:
            job_description = jd_text

        with st.spinner("Extracting text from Resume..."):
            from utils.ingestion import get_pdf_text_pdfplumber

            try:
                resume_text = get_pdf_text_pdfplumber(uploaded_resume)
            except Exception as exc:
                st.error(f"☠️ An error occurred reading the PDF: {uploaded_resume}")
                logger.exception("Resume extraction failed: %s", exc)
                st.stop()

        if resume_text and job_description:
            try:
                progress_bar = st.progress(1, text="Initializing AI 🧠 ..")

                rag_run_config = {}
                enable_verbose = os.getenv("VERBOSE_RAG_LOGS", "false").lower() == "true"
                if enable_verbose:
                    from utils.logging_setup import DebugCallbackHandler

                    logger.info("🔧 Verbose RAG Logging is ENABLED")
                    rag_run_config = {"callbacks": [DebugCallbackHandler()]}
                else:
                    logger.info("🔧 Verbose RAG Logging is DISABLED")

                progress_bar.progress(5, text="Extracting Job Metadata... (5%)")
                results = run_candidate_analysis(
                    resume_text=resume_text,
                    resume_file_name=uploaded_resume.name,
                    job_description=job_description,
                    rag_run_config=rag_run_config,
                )

                progress_bar.progress(100, text="Analysis Complete! (100%)")
                progress_bar.empty()

                st.session_state["analysis_results"] = results
                st.session_state["full_report"] = results["report"]

                st.success("✅ Analysis and Assessment Completed ..!")
                logger.info("✅ Analysis and Assessment Completed ..!")

            except Exception as exc:
                st.error(f"☠️ An error occurred: {exc}")
                logger.exception("Analysis failed: %s", exc)
                st.stop()

    if st.session_state["analysis_results"]:
        results = st.session_state["analysis_results"]

        st.markdown("---")
        st.subheader("📊 Analysis Results")

        tabs = st.tabs(["Fit Analysis", "Strengths & Weaknesses", "Cover Letter & Tips", "Interview Tips"])

        with tabs[0]:
            st.markdown("### 🎯 Fit Assessment")
            st.metric(label="Match Score:", value=f"{results['score']}%")
            st.progress(results["score"] / 100)

            if results["score"] < 50:
                st.error("Low Match - Missing critical skills.")
            elif results["score"] < 80:
                st.warning("Good Match - Some gaps identified.")
            else:
                st.success("High Match - Strong candidate!")

            with st.expander("**Skills Check:**"):
                st.write(results["q1"])

            with st.expander("**Fit Check:**"):
                st.write(results["q2"])

        with tabs[1]:
            st.markdown("### 📈 SWOT Analysis")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info("Strengths", icon="💪")
                st.write(results["q4"])
            with col2:
                st.warning("Opportunities", icon="🌤️")
                st.write(results["q5"])
            with col3:
                st.error("Weaknesses", icon="🚨")
                st.write(results["q6"])

        with tabs[2]:
            st.markdown("### 📝 Application Kit")
            with st.expander("Draft Cover Letter"):
                st.write(results["q7"])
            with st.expander("**How to Stand Out:**"):
                st.write(results["q8"])

        with tabs[3]:
            st.subheader("🎤 Interview Elevator Pitch")
            st.info(results["q9"])

        st.divider()
        st.subheader("📥 Export Report")
        st.download_button(
            label="Download Full Analysis Report (Markdown/Text)",
            data=st.session_state["full_report"],
            file_name="candidate_analysis.md",
            mime="text/markdown",
        )

        st.divider()
        st.subheader("💾 Save to Job Tracker")
        st.markdown("Add this analysis directly to your pipeline.")

        with st.form("save_to_tracker_form"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                company_input = st.text_input("Company Name*", value=results.get("company", ""))
            with col2:
                title_input = st.text_input("Job Title*", value=results.get("title", ""))
            with col3:
                score_val = results.get("score", 0)
                st.metric("Match Score", f"{score_val}%")

            save_btn = st.form_submit_button("Save to Tracker")

            if save_btn:
                if company_input and title_input:
                    df = load_tracker_data()
                    new_entry = pd.DataFrame(
                        [
                            {
                                "Date Applied": datetime.today().strftime("%Y-%m-%d"),
                                "Company": company_input,
                                "Job Title": title_input,
                                "Match Score": score_val,
                                "Status": "Applied",
                                "URL": jd_url if jd_url else jd_text,
                                "Notes": f"AI Analysis mapped from resume: {uploaded_resume.name}",
                                "Report": st.session_state.get("full_report", ""),
                            }
                        ]
                    )

                    df = pd.concat([df, new_entry], ignore_index=True)
                    save_tracker_data(df)

                    st.session_state["tracker_success_msg"] = (
                        f"Successfully saved {title_input} at {company_input}!"
                    )
                    st.rerun()
                else:
                    st.error("⚠️ Please enter both the Company Name and Job Title to save.")