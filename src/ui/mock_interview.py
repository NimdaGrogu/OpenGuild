from __future__ import annotations

import io
import logging

import pandas as pd
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from data.tracker_repository import load_tracker_data
from services.interview_service import MockInterviewEngine
from utils.css_template import buttom_style
logger = logging.getLogger("mock_interview")


def render_mock_interview():
    # ---------------------------------------------------------
    # CSS INJECTION: Beautiful glowing buttons
    # ---------------------------------------------------------
    st.markdown(buttom_style, unsafe_allow_html=True)

    st.header("🎤 AI Mock Interview")
    st.markdown("Practice your interview skills with an **AI Hiring Coach** tailored for you and the target job.")

    # MockInterview Engine (Assumes initialized elsewhere)
    interview_eng = MockInterviewEngine()

    if 'mockinterview_success_msg' in st.session_state:
        st.toast(st.session_state['mockinterview_success_msg'], icon="✅")
        del st.session_state['mockinterview_success_msg']

    # 1. Load data from the Job Tracker
    df = load_tracker_data()

    if df.empty:
        st.toast("Your Job Tracker is empty. Please analyze a job and save it to the tracker first.", icon="⚠️")
        return

    # 2. Job Selection UI
    st.subheader("1. Select a Saved Application")
    df['Job_Label'] = df['Company'] + " - " + df['Job Title']
    job_options = ["-- Select an Application --"] + df['Job_Label'].tolist()

    selected_job_label = st.selectbox("Choose a role to interview for:", job_options, key="job_selector")

    if selected_job_label == "-- Select an Application --":
        st.toast("Please select a job from the dropdown above to begin.", icon="⚠️")
        return

    selected_idx = job_options.index(selected_job_label) - 1
    selected_row = df.iloc[selected_idx]
    company = selected_row['Company']
    title = selected_row['Job Title']
    candidate_report = "No prior evaluation available for this candidate." if pd.isna(selected_row.get('Report')) else \
    selected_row['Report']

    st.caption(f"**Current Context:** Interviewing for {title} at {company}")
    st.divider()

    #######################
    # STATE INITIALIZATION (The New Engine)
    #######################
    # phase can be: 'setup', 'ai_thinking', 'user_turn', 'evaluation'
    if 'phase' not in st.session_state:
        st.session_state['phase'] = 'setup'

    # turn_count generates a fresh audio widget every turn to prevent crash bugs
    if 'turn_count' not in st.session_state:
        st.session_state['turn_count'] = 0

    # Stores the text that needs to be sent to the AI
    if 'pending_input' not in st.session_state:
        st.session_state['pending_input'] = ""

    if 'interview_messages' not in st.session_state:
        st.session_state['interview_messages'] = []

    #######################
    # INTERVIEW CONTROLS (Sidebar)
    #######################
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Interview Controls:")

        start_btn = st.button("🟢 Start Interview", type="primary", use_container_width=True)
        end_btn = st.button("🛑 End Interview", type="secondary", use_container_width=True)

        if st.button("🔄 Start Fresh", type="secondary", use_container_width=True):
            keys_to_delete = ['interview_messages', 'current_interview_job', 'phase', 'turn_count', 'pending_input',
                              'autoplay_next', 'job_selector']
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    #######################
    # DYNAMIC JOB SWITCH RESET
    #######################
    if st.session_state.get('current_interview_job') != selected_job_label:
        st.session_state['current_interview_job'] = selected_job_label
        st.session_state['phase'] = 'setup'
        st.session_state['turn_count'] = 0
        st.session_state['pending_input'] = ""
        st.session_state['interview_messages'] = []

        greeting_text = (
            f"Hi there! I'm OpenGuild, your Coach Assistant. I'll be acting as the hiring manager for the {title} "
            f"position at {company} today.\r\n\r\n"
            f"To kick things off, press the Start Interview button in the sidebar."
        )

        with st.spinner("🛠️ Setting everything up ..."):
            greeting_audio = interview_eng.generate_tts(greeting_text)
            st.audio(greeting_audio, format="audio/mp3", width=300, autoplay=True if greeting_audio else False)
            st.write(f"✨  {greeting_text}")

    #######################
    # EVALUATION MODE
    #######################
    if end_btn or st.session_state['phase'] == 'evaluation':
        st.session_state['phase'] = 'evaluation'
        st.subheader("📊 Interview Performance Report")
        st.info("The interview has ended.")
        transcript = ""
        for msg in st.session_state.interview_messages:
            speaker = "Interviewer" if isinstance(msg, AIMessage) else "Candidate"
            transcript += f"**{speaker}:** {msg.content}\n\n"
        with st.spinner("Analyzing your responses and building feedback..."):
            feedback = interview_eng.evaluation_report(title=title,
                                            company=company,
                                            transcript=transcript,
                                            evaluation_report=candidate_report
                                            )
            st.markdown(feedback)
            st.divider()
        st.stop()

    ##########################################################
    #  THE STATE MACHINE (Strict Isolated Phases)          #
    ##########################################################

    # 1. TRIGGER START
    if start_btn and st.session_state['phase'] == 'setup':
        st.session_state['phase'] = 'ai_thinking'
        st.session_state['pending_input'] = "Hello! I am ready to begin. Please ask the first interview question."
        st.session_state['turn_count'] = 1
        st.rerun()

    # 2. ALWAYS RENDER CHAT HISTORY (Unless in setup)
    if st.session_state['phase'] != 'setup':
        for idx, msg in enumerate(st.session_state['interview_messages']):
            role = "assistant" if isinstance(msg, AIMessage) else "user"

            # Hide system commands
            is_hidden_command = role == "user" and (
                        "I am ready to begin" in msg.content or "skip this question" in msg.content)
            if is_hidden_command:
                continue

            avatar = "✨" if role == "assistant" else "👤"

            with st.chat_message(role, avatar=avatar):
                st.write(msg.content)

                if isinstance(msg, AIMessage) and "tts_audio" in msg.additional_kwargs:
                    is_last = (idx == len(st.session_state['interview_messages']) - 1)
                    should_autoplay = is_last and st.session_state.get('autoplay_next', False)
                    audio_bytes = msg.additional_kwargs["tts_audio"]
                    st.audio(io.BytesIO(audio_bytes), format="audio/mp3", autoplay=should_autoplay, width=300)
                    if should_autoplay:
                        st.session_state['autoplay_next'] = False

        st.markdown("---")

    # 3. PHASE: AI IS THINKING
    if st.session_state['phase'] == 'ai_thinking':
        # Safely append user input exactly once
        user_input = st.session_state['pending_input']
        if user_input:
            st.session_state['interview_messages'].append(HumanMessage(content=user_input))

        # Generate response exactly once
        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("🧠 The interviewer is processing..."):
                response = interview_eng.chat_interview(
                    title=title,
                    company=company,
                    candidate_report=candidate_report,
                    history=st.session_state['interview_messages'][:-1],
                    user_input=user_input
                )
                audio_content = interview_eng.generate_tts(response)

        # Store response
        st.session_state['interview_messages'].append(
            AIMessage(
                content=response,
                additional_kwargs={"tts_audio": audio_content} if audio_content else {}
            )
        )
        st.session_state['autoplay_next'] = True

        # Phase Complete! Switch to user's turn and wipe the pending input
        st.session_state['pending_input'] = ""
        st.session_state['phase'] = 'user_turn'
        st.rerun()

    # 4. PHASE: USER'S TURN (Microphone Mode)
    elif st.session_state['phase'] == 'user_turn':
        col_mic, col_skip = st.columns([3, 1], vertical_alignment="bottom")

        with col_mic:
            # The widget key uses 'turn_count'. It is a completely new widget every turn.
            recorded_audio = st.audio_input("🎙️ Record your answer",
                                            width="stretch",
                                            key=f"mic_input_{st.session_state['turn_count']}"
                                            )
        with col_skip:
            skip_btn = st.button("⏭️ Skip Question", key=f"skip_btn_{st.session_state['turn_count']}",
                                 use_container_width=True)

        # Process the input if they clicked/spoke
        if recorded_audio:
            audio_bytes = recorded_audio.getvalue()
            with st.spinner("🎤 Processing your audio..."):
                transcribed_text = interview_eng.transcribe_audio(audio_bytes)
                if transcribed_text:
                    st.session_state['pending_input'] = transcribed_text
                    st.session_state['turn_count'] += 1
                    st.session_state['phase'] = 'ai_thinking'
                    st.rerun()

        elif skip_btn:
            st.session_state['pending_input'] = "I'm stuck on this one. Let's skip it and move to the next question."
            st.session_state['turn_count'] += 1
            st.session_state['phase'] = 'ai_thinking'
            st.rerun()
