from langchain_core.callbacks import BaseCallbackHandler
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

def load_tracker_data_():
    """Loads the job tracker data from a CSV, or creates an empty DataFrame if it doesn't exist."""
    TRACKER_FILE = "job_tracker.csv"

    if os.path.exists(TRACKER_FILE):
        df = pd.read_csv(TRACKER_FILE, parse_dates=["Date Applied"])
        if "Report" not in df.columns:
            df["Report"] = ""
        return df
    else:
        # Define the columns for a new tracker
        # Define default columns with correct types
        # --- NEW: Ensure older CSVs get the new column without crashing ---
        # --- NEW: Add "Report" to the default columns ---
        df = pd.DataFrame(columns=[
            "Date Applied", "Company", "Job Title", "Match Score", "Status", "URL", "Notes", "Report"
        ])
        # Force empty column type to datetime so editor doesn't complain on first load
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