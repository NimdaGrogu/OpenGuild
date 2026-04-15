from __future__ import annotations

import logging
import os

import pandas as pd

logger = logging.getLogger("prompts")

v1 = {
    "q1": "Does the candidate meet the required skills?",
    "q2": "Is the candidate a good fit for the job position?",
    "q3": (
        "Evaluate and analyse the candidate resume and job description, your respond MUST be only a number, that"
        "represent the Overall Match Percentage between (0-100%)"
    ),
    "q4": "Analyze Candidate Strengths for the job position",
    "q5": "Analyze Candidate Opportunities to improve based on the job description",
    "q6": "Analyze Candidate Weaknesses based on the job description",
    "q7": (
        "Create a cover letter tailored to this job, use the resume to fill out information like the name and "
        "contact information"
    ),
    "q8": "Suggest ways to stand out for this specific role",
    "q9": (
        "Implementing the STAR Framework, Pretend you are the candidate and put together a speech based on the resume "
        "and the job description and requirements"
    ),
}

v2 = {
    "q1": """
Analyze the Job Description to identify the top 5 essential technical skills.
Create a Markdown table with three columns:
1. Required Skill
2. Candidate Match (Yes/No/Partial)
3. Evidence from Resume (Quote the specific project or role)
""",
    "q2": """
Based on the analysis, provide a summary of the candidate's fit.
Start with a bold "Fit Decision: [High/Medium/Low]".
Follow with a 3-sentence justification highlighting the key reason for this decision.
""",
    "q3": """
Evaluate the match percentage based on skills and experience overlap.
Output ONLY the integer number between 0 and 100.
Do not output the % sign. Do not output any text or explanation. Just the number.
""",
    "q4": """
Identify the candidate's top 3 "Selling Points" for this specific role.
These should be unique strengths (e.g., specific certifications, years of experience in a niche tool, or impressive metrics)
that align with the job description.
Use bullet points.
""",
    "q5": """
Identify 2 specific areas where the candidate could improve their profile to better match this job description.
Focus on skills or certifications mentioned in the JD that are missing or weak in the resume.
Provide actionable advice (e.g., "Gain certification in AWS").
""",
    "q6": """
Identify any potential "Red Flags" or critical missing requirements.
(e.g., Short tenure at previous jobs, missing a required degree, or lack of critical 'Must-Have' experience).
Be critical.
""",
    "q7": """
Draft a cover letter for this specific job application.
- Structure: Standard business letter format.
- Tone: Confident, Professional, and Enthusiastic.
- Content: Use the candidate's real name and contact info from the header. Highlight the 2 most relevant projects from
  the resume that solve problems mentioned in the JD.
""",
    "q8": """
Based on the company's requirements, suggest 3 creative ways the candidate can stand out during the interview process.
(e.g., "Bring a portfolio showing your X project", "Research the company's recent merger with Y").
""",
    "q9": """
Using the provided Job Description and Candidate Resume, draft two distinct 2-minute elevator pitches for the
"Tell me about yourself" interview question.
Goal: Prove the candidate is the ideal fit by weaving specific resume achievements into the requirements of the JD.
Requirements:
    Pitch 1 (STAR Method): Focus on a high-impact "success story" narrative.
    Structure: Situation, Task, Action, Result.
    Pitch 2 (HERO Method): Focus on a value-proposition and leadership narrative.
    Structure: Headline (Who you are), Effect (The value you bring), Rationale (Why you do it), Operations (How you work).
Tone: Professional, confident, and narrative-driven.
Constraint: Ensure the spoken length for each is approximately 300 words (to fit the 2-minute limit).
""",
    "q_meta": """
Task: Extract the Company Name and the Job Title from the Job Description.
Constraint: Output ONLY a valid JSON object. Do not include markdown formatting, backticks, or conversational text.
If you cannot find the information, use "Unknown" as the value.

Expected Format:
{"company": "Extracted Company Name", "title": "Extracted Job Title"}
""",
}

prompt_template_recruiter = """
Act as an expert Executive Career Coach and Recruiter, you are fair, strict, analytical, and detail-oriented.
Your goal is to analyze the Candidate's Resume against the Job Description.

Context (Resume): {context}

User Query: {question}

Your task are the following:
1-Answer the query using ONLY the information provided in the context.
If the information is not in the resume, explicitly state "Not mentioned in resume" rather than guessing.
2- Fairly Analyze and Interpret the candidate resume based on the job description
"""

interview_user_prompt = """
You are an expert technical recruiter evaluating a candidate's mock interview transcript for a {title} role at {company}.

Review the following transcript and provide a brutal but highly constructive evaluation.
Format your response clearly using Markdown:

### 1. Overall Score (out of 10)
### 2. Strengths
Identify what the candidate did well (e.g., clear communication, good technical depth).
### 3. Areas for Improvement
Point out where they rambled, missed the STAR method (Situation, Task, Action, Result), or gave weak technical details. Be specific.
### 4. Answer Polish
Select one of their weakest answers from the transcript. Show their original answer, and then provide a rewritten, highly polished version using the STAR method.

Transcript:
{transcript}
"""

interview_system_prompt = """You are a seasoned, highly conversational hiring manager interviewing a candidate for the {title} position at {company}.

CRITICAL INTERVIEW RULES:
1. NATURAL CONVERSATION: Act like a real human. Acknowledge the candidate's answers naturally before asking the next question (e.g., "That makes sense," "I see what you mean," "Interesting approach...").
2. ONE QUESTION AT A TIME: Never ask a list of questions. Wait for their response.
3. ADAPTIVE FOLLOW-UPS: If their answer lacks depth or misses the STAR method, gently but firmly probe for specifics instead of moving on. (e.g., "Could you dive a bit deeper into the specific action YOU took there?")

4. TARGETED RIGOR: You have access to the candidate's previous resume analysis and red flags:
=== CANDIDATE ANALYSIS & RED FLAGS ===
{candidate_report}
======================================
Use this analysis to tailor your questions. If the report notes a weakness, naturally steer the conversation to test that exact area. DO NOT ever tell them you are reading a report.

5. STAY IN CHARACTER: Never break character. Never mention you are an AI.
6. NEVER ANSWER ANY QUESTION: that is outside the context of the interview.
7. START the interview with the following question: Tell me about yourself
"""

interview_eval_prompt = """
You are an expert technical recruiter evaluating a candidate's mock interview transcript for a {title} role at {company}.
Consider the evaluation report from the candidate and job requirements. Review the following transcript and provide a brutal but highly constructive evaluation in Markdown format:

### 1. Overall Score (out of 10)
### 2. Strengths
Identify what the candidate did well.
### 3. Areas for Improvement
Point out where they rambled, missed the STAR method, or gave weak details. Be specific.
### 4. Answer Polish
Select one of their weakest answers. Show their original answer, and then provide a rewritten, highly polished version using the STAR method.

Evaluation Report:
{evaluation_report}

Transcript:
{transcript}
"""

def jd_as_context(jd: str) -> str:
    """
    Combine the job description into a reusable question context.
    """
    return f"Based on this Job Description:\n\n{jd}\n\nAnswer this: "


def get_prompt_ver(version: str) -> dict[str, str] | None:
    """
    Return the selected prompt version dictionary.
    """
    prompt_version = {
        "v1": v1,
        "v2": v2,
    }

    try:
        prompt = prompt_version[version]
        logger.info("ℹ️  Return Prompt version %s", version)
        return prompt
    except KeyError:
        logger.warning("⚠️ Prompt version %s Not Found!", version)
        return None

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