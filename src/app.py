import os
import streamlit as st
from streamlit_option_menu import option_menu

# ... existing code ...

def main() -> None:
    st.set_page_config(
        page_title="OpenGuild Job Hunt Assistant",
        page_icon="🚀",
        layout="wide",
    )

    with st.sidebar:
        st.title("OpenGuild")
        selected = option_menu(
            menu_title="Main Menu",
            options=["Candidate Coach", "Job Tracker", "Mock Interview"],
            icons=["robot", "clipboard-data", "mic"],
            menu_icon="cast",
            default_index=0,
        )

    if selected == "Candidate Coach":
        from ui.candidate_coach import render_candidate_coach
        render_candidate_coach()
    elif selected == "Job Tracker":
        from ui.job_tracker import render_job_tracker
        render_job_tracker()
    elif selected == "Mock Interview":
        from ui.mock_interview import render_mock_interview
        render_mock_interview()


if __name__ == "__main__":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    main()
