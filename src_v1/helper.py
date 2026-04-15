from prompt_eng import interview_eval_prompt, interview_system_prompt
from langchain_openai import ChatOpenAI
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks import BaseCallbackHandler
import io
import re
import logging
import os
import pandas as pd


logger = logging.getLogger("helper_debugger")

def extract_match_score(response_text):
    # Search for a number between 0 and 100
    match = re.search(r'\b(100|[1-9]?[0-9])\b', response_text)
    if match:
        return int(match.group(0))
    return 0

def load_tracker_data():
    """
    Bulletproof loader for job tracker data.
    Ensures 'Date Applied' is forced to datetime type regardless of CSV structure.
    """
    df = None  # Initialize empty variable
    TRACKER_FILE = "job_tracker.csv"

    if os.path.exists(TRACKER_FILE):
        # 1. Load the data normally as strings/objects first
        df = pd.read_csv(TRACKER_FILE)

        # 2. Force the conversion immediately after loading.
        # We tell Pandas to expect "YYYY-MM-DD" format, which is what we save.
        # errors='coerce' turns unparseable values into 'NaT' (Not a Time), preventing a crash.
        try:
            # We use ISO8601 as that's the strict standard (YYYY-MM-DD)
            # You might need format='%Y-%m-%d' depending on exactly how it's saved.
            df['Date Applied'] = pd.to_datetime(df['Date Applied'], format='ISO8601', errors='coerce')
        except Exception as e:
            # If standard ISO fails, try mixed format
            print(f"ISO parse failed, trying mixed: {e}")
            df['Date Applied'] = pd.to_datetime(df['Date Applied'], format='mixed', errors='coerce')

        # Cleanup: Remove any fully empty rows that might have been accidentally saved
        df = df.dropna(how='all')
    else:
        # Define default columns
        df = pd.DataFrame(columns=[
            "Date Applied", "Company", "Job Title", "Match Score", "Status", "URL", "Notes"
        ])

    # 3. Handle First-Run Integrity: Even for empty dfs or cases where loading failed,
    # we must guarantee the type of this column so charts/editors don't complain.
    # We force the empty or Nat-filled column to be a specialized datetime type.
    df["Date Applied"] = pd.to_datetime(df["Date Applied"])

    return df

def save_tracker_data(df):
    TRACKER_FILE = "job_tracker.csv"
    """Saves the DataFrame to the CSV file."""
    df.to_csv(TRACKER_FILE, index=False)

class DebugCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Run when LLM starts running. This gives us the FINAL prompt sent to the LLM."""
        logger.info("============== 📤 PROMPT SENT TO MODEL ==============")
        # prompts[0] is the final string with context and question injected
        logger.info(prompts[0])
        logger.info("=====================================================")

    def on_llm_end(self, response, **kwargs):
        """Run when LLM ends running."""
        logger.info("============== 📥 RESPONSE FROM MODEL ===============")
        # Access the actual text generated
        logger.info(response.generations[0][0].text)
        logger.info("=====================================================")

class MockInterviewEngine:
    logger.info(f" ✅  Executing mocking interview engine ..")
    def __init__(self):
        self.llm = ChatOpenAI(model='gpt-4o', temperature=0.7)
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


    # ==========================================
    # HELPER FUNCTIONS: AUDIO & TTS
    # ==========================================
    def transcribe_audio(self, audio_bytes):
        """Passes raw audio bytes to OpenAI's Whisper model for speech-to-text."""
        try:

            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            return transcript
        except Exception as e:
            logger.error(f"⚠️ Audio transcription failed: {e}")
            return None

    def generate_tts(self, text):
        """Passes text to OpenAI's TTS model and returns the audio bytes."""
        try:

            response = self.client.audio.speech.create(
                model="tts-1",
                voice="onyx",  # Options: alloy, echo, fable, onyx, nova, shimmer
                input=text
            )
            return response.content
        except Exception as e:
            logger.error(f"⚠️ Text-to-Speech failed: {e}")
            return None
    # ---------------------------------------------------------
    #  EVALUATION REPORT (Runs when interview ends)
    # ---------------------------------------------------------
    def evaluation_report(self, title, company, transcript, evaluation_report):
        """eval_prompt = interview_eval_prompt.format(evaluation_report=evaluation_report,
                                                   company=company,
                                                   title=title,
                                                   transcript=transcript)


        feedback = self.llm.invoke(eval_prompt)
        return feedback.content
        """
        eval_prompt = ChatPromptTemplate.from_template(interview_eval_prompt)

        feedback = (eval_prompt | self.llm).invoke({
            "title": title,
            "company": company,
            "transcript": transcript,
            "evaluation_report" : evaluation_report
        })

        return feedback.content

    def chat_interview(self, title:str, company:str, candidate_report:str, history, user_input):
        system_prompt = interview_system_prompt.format(
                                       title=title,
                                       company=company,
                                       candidate_report=candidate_report
                                       )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        response = (prompt | self.llm).invoke({
            "history": history,
            "input": user_input
        })

        return response.content