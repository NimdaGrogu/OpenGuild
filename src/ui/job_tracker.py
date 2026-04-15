from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import streamlit as st

from data.tracker_repository import load_tracker_data, save_tracker_data

logger = logging.getLogger("job_tracker")


def render_job_tracker() -> None:
    """
    Render the Job Tracker page.
    """
    if "tracker_success_msg" in st.session_state:
        st.toast(st.session_state["tracker_success_msg"], icon="✅")
        del st.session_state["tracker_success_msg"]

    st.header("📊 Job Tracker tool")
    st.markdown("Keep track of your job applications, scores, and interview statuses.")

    df = load_tracker_data()

    with st.expander("➕ Add New Application", expanded=False):
        with st.form("add_job_form"):
            colA, colB = st.columns(2)
            with colA:
                new_company = st.text_input("Company Name*")
                new_title = st.text_input("Job Title*")
                new_score = st.number_input("Match Score (%)", min_value=0, max_value=100, value=0)
            with colB:
                new_status = st.selectbox(
                    "Status",
                    ["Applied", "Screening", "Interviewing", "Offer", "Rejected", "Ghosted"],
                )
                new_url = st.text_input("Job URL")
                new_date = st.date_input("Date Applied", datetime.today())

            new_notes = st.text_area("Notes (e.g., recruiter name, next steps)")
            submit_job = st.form_submit_button("Save Application")

            if submit_job:
                if new_company and new_title:
                    new_row = pd.DataFrame(
                        [
                            {
                                "Date Applied": new_date.strftime("%Y-%m-%d"),
                                "Company": new_company,
                                "Job Title": new_title,
                                "Match Score": new_score,
                                "Status": new_status,
                                "URL": new_url,
                                "Notes": new_notes,
                                "Report": "",
                            }
                        ]
                    )
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_tracker_data(df)
                    st.session_state["tracker_success_msg"] = (
                        f"✅ Job Application Added: Job Title {new_title} at {new_company}!"
                    )
                    st.rerun()
                else:
                    st.error("⚠️ Company Name and Job Title are required.")

    st.subheader("📋 Your Applications")
    if not df.empty:
        edited_df = st.data_editor(
            df,
            width="stretch",
            num_rows="dynamic",
            column_config={
                "Date Applied": st.column_config.DateColumn(
                    "Date Applied",
                    help="The day you submitted the application",
                    format="YY-MM-DD",
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
                "URL": st.column_config.LinkColumn("Job Link"),
                "Report": None,
            },
        )

        if not edited_df.astype(str).equals(df.astype(str)):
            save_tracker_data(edited_df)
            st.session_state["tracker_success_msg"] = "Tracker successfully updated!"
            st.rerun()

        st.divider()
        st.subheader("📄 View Saved Job Assessments")

        df["Report"] = df["Report"].fillna("")
        jobs_with_reports = df[df["Report"] != ""]

        if not jobs_with_reports.empty:
            dropdown_options = jobs_with_reports.apply(
                lambda x: f"{x['Company']} - {x['Job Title']}", axis=1
            ).tolist()

            selected_job_label = st.selectbox(
                "Select an application to read its AI Analysis:",
                ["-- Select an Application --"] + dropdown_options,
            )

            if selected_job_label != "-- Select an Application --":
                selected_idx = dropdown_options.index(selected_job_label)
                actual_report_text = jobs_with_reports.iloc[selected_idx]["Report"]

                with st.container(height=600, border=True):
                    st.markdown(actual_report_text)
        else:
            st.info("No AI reports saved yet. Analyze a job and click 'Save to Tracker' to see them here.")

    st.divider()
    st.subheader("📈 Quick Stats")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Total Applied", len(df))
    col2.metric("Interviewing", len(df[df["Status"] == "Interviewing"]) if not df.empty else 0)
    col3.metric("Offers", len(df[df["Status"] == "Offer"]) if not df.empty else 0)
    col4.metric("Rejected", len(df[df["Status"] == "Rejected"]) if not df.empty else 0)
    col5.metric("Ghosted", len(df[df["Status"] == "Ghosted"]) if not df.empty else 0)
    col6.metric("Screening", len(df[df["Status"] == "Screening"]) if not df.empty else 0)

    st.markdown("---")
    st.subheader("📈 Application Insights")

    if not df.empty:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("**Pipeline Status**")
            status_counts = df["Status"].value_counts()
            st.bar_chart(status_counts)

        with chart_col2:
            st.markdown("**Application Activity Over Time**")
            timeline_counts = df.groupby(df["Date Applied"].dt.date).size()
            st.line_chart(timeline_counts)
    else:
        st.info("Add some applications to see your visual insights!")

    st.markdown("---")