from __future__ import annotations

import io
import logging

import pandas as pd
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from data.tracker_repository import load_tracker_data
from services.interview_service import MockInterviewEngine

logger = logging.getLogger("mock_interview")


def render_mock_interview() -> None:
    """
    Render the Mock Interview page.
    """
    st.markdown(
        """
        <style>
        div.stButton > button:first-child {
            border-radius: 20px;
            border: 1px solid #4B4B4B;
            transition: all 0.3s ease-in-out;
            font-weight: 600;
        }
        div.stButton > button:first-child:hover {
            border: 1px solid #FF4B4B;
            box-shadow: 0px 0px 10px rgba(255, 75, 75, 0.4);
            transform: translateY(-2px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("🎤 AI Mock Interview")
    st.markdown("Practice your interview skills with an **AI Hiring Coach** tailored for you and the target job.")

    interview_eng = MockInterviewEngine()

    if "mockinterview_success_msg" in st.session_state:
        st.toast(st.session_state["mockinterview_success_msg"], icon="✅")
        del st.session_state["mockinterview_success_msg"]

    df = load_tracker_data()
    if df.empty:
        st.toast("Your Job Tracker is empty. Please analyze a job and save it to the tracker first.", icon="⚠️")
        return

    st.subheader("1. Select a Saved Application")
    df["Job_Label"] = df["Company"] + " - " + df["Job Title"]
    job_options = ["-- Select an Application --"] + df["Job_Label"].tolist()

    selected_job_label = st.selectbox("Choose a role to interview for:", job_options, key="job_selector")

    if selected_job_label == "-- Select an Application --":
        st.toast("Please select a job from the dropdown above to begin.", icon="⚠️")
        return

    selected_idx = job_options.index(selected_job_label) - 1
    selected_row = df.iloc[selected_idx]
    company = selected_row["Company"]
    title = selected_row["Job Title"]
    candidate_report = (
        "No prior evaluation available for this candidate."
        if pd.isna(selected_row.get("Report"))
        else selected_row["Report"]
    )

    st.caption(f"**Current Context:** Interviewing for {title} at {company}")
    st.divider()

    if "phase" not in st.session_state:
        st.session_state["phase"] = "setup"
    if "turn_count" not in st.session_state:
        st.session_state["turn_count"] = 0
    if "pending_input" not in st.session_state:
        st.session_state["pending_input"] = ""
    if "interview_messages" not in st.session_state:
        st.session_state["interview_messages"] = []

    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Interview Controls:")

        start_btn = st.button("🟢 Start Interview", type="primary", use_container_width=True)
        end_btn = st.button("🛑 End Interview", type="secondary", use_container_width=True)

        if st.button("🔄 Start Fresh", type="secondary", use_container_width=True):
            keys_to_delete = [
                "interview_messages",
                "current_interview_job",
                "phase",
                "turn_count",
                "pending_input",
                "autoplay_next",
                "job_selector",
            ]
            for key in keys_to_delete:
                st.session_state.pop(key, None)
            st.rerun()

    if st.session_state.get("current_interview_job") != selected_job_label:
        st.session_state["current_interview_job"] = selected_job_label
        st.session_state["phase"] = "setup"
        st.session_state["turn_count"] = 0
        st.session_state["pending_input"] = ""
        st.session_state["interview_messages"] = []

        greeting_text = (
            f"Hi there! I'm OpenGuild, your Coach Assistant. I'll be acting as the hiring manager for the {title} "
            f"position at {company} today.\r\n\r\n"
            f"To kick things off, press the Start Interview button in the sidebar."
        )

        with st.spinner("🛠️ Setting everything up ..."):
            greeting_audio = interview_eng.generate_tts(greeting_text)
            st.audio(greeting_audio, format="audio/mp3", width=300, autoplay=True if greeting_audio else False)