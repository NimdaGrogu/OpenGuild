import logging
from rich.logging import RichHandler
# Configure basic config with RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s", # Rich handles the timestamp and level separately
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("prompt_eng")

v1 = {
            "q1": "Does the candidate meet the required skills?",
            "q2": "Is the candidate a good fit for the job position?",
            "q3": "Evaluate and analyse the candidate resume and job description, your respond MUST be only a number, that"
                  "represent the Overall Match Percentage between (0-100%)",
            "q4": "Analyze Candidate Strengths for the job position",
            "q5": "Analyze Candidate Opportunities to improve based on the job description",
            "q6": "Analyze Candidate Weaknesses based on the job description",
            "q7": "Create a cover letter tailored to this job, use the resume to fill out information like the name and "
                  "contact information",
            "q8": "Suggest ways to stand out for this specific role",
            "q9": "Implementing the STAR Framework, Pretend you are the candidate and put together a speech based on the resume and the job"
                  "description and requirements"
        }

v2 = {
    # q1: Changed to a Table for easy reading.
    # We ask for "Evidence" to prevent the AI from hallucinating skills.
    "q1": """
    Analyze the Job Description to identify the top 5 essential technical skills.
    Create a Markdown table with three columns: 
    1. Required Skill
    2. Candidate Match (Yes/No/Partial)
    3. Evidence from Resume (Quote the specific project or role)
    """,

    # q2: Changed to force a decision + reasoning.
    "q2": """
    Based on the analysis, provide a summary of the candidate's fit.
    Start with a bold "Fit Decision: [High/Medium/Low]".
    Follow with a 3-sentence justification highlighting the key reason for this decision.
    """,

    # q3: Extremely strict to ensure your Python regex code works.
    "q3": """
    Evaluate the match percentage based on skills and experience overlap.
    Output ONLY the integer number between 0 and 100.
    Do not output the % sign. Do not output any text or explanation. Just the number.
    """,

    # q4: Focus on "selling points".
    "q4": """
    Identify the candidate's top 3 "Selling Points" for this specific role. 
    These should be unique strengths (e.g., specific certifications, years of experience in a niche tool, or impressive metrics) that align with the job description.
    Use bullet points.
    """,

    # q5: "Opportunities" usually means "Upskilling".
    "q5": """
    Identify 2 specific areas where the candidate could improve their profile to better match this job description.
    Focus on skills or certifications mentioned in the JD that are missing or weak in the resume.
    Provide actionable advice (e.g., "Gain certification in AWS").
    """,

    # q6: "Weaknesses" refers to hard gaps (Dealbreakers).
    "q6": """
    Identify any potential "Red Flags" or critical missing requirements.
    (e.g., Short tenure at previous jobs, missing a required degree, or lack of critical 'Must-Have' experience).
    Be critical.
    """,

    # q7: Added "Tone" and "Structure" to make it usable.
    "q7": """
    Draft a cover letter for this specific job application.
    - Structure: Standard business letter format.
    - Tone: Confident, Professional, and Enthusiastic.
    - Content: Use the candidate's real name and contact info from the header. Highlight the 2 most relevant projects from 
      the resume that solve problems mentioned in the JD.
    """,

    # q8: Differentiators.
    "q8": """
    Based on the company's requirements, suggest 3 creative ways the candidate can stand out during the interview process.
    (e.g., "Bring a portfolio showing your X project", "Research the company's recent merger with Y").
    """,

    # q9: "Elevator Pitch" is a better term than "Speech".
    "q9": """
    Consider the Job requirements and Candidate resume Using the STAR Method (Situation, Task, Action, Result), 
    draft a 2-minute "Elevator Pitch" for the candidate to use at the start of an interview.
    
    - The pitch should answer "Tell me about yourself" by weaving the resume experience and matched skills into a narrative that proves the
      candidate is the perfect fit for THIS job description.
    """
}

# Define the Prompt, this tells the LLM how to behave
prompt_template = """
        Act as a Senior Technical Recruiter, you are fair, strict, analytical, and detail-oriented.
        Your goal is to analyze the Candidate's Resume against the Job Description.

        Context (Resume): {context}

        User Query: {question}

        Your task are the following:
        1-Answer the query using ONLY the information provided in the context. 
        If the information is not in the resume, explicitly state "Not mentioned in resume" rather than guessing.
        2- Fairly Analyze and Interpret the candidate resume based on the job description and provide a professional assessment.
        """

def jd_as_context(jd: str)->str:
    """
    This function creates a Based Query that combines the job description
    :param jd:
    :return:
    """
    # Combining the Job Description as a context in the base query
    base_query = f"Based on this Job Description: \n\n {jd} \n\n Answer this: "
    return base_query

def get_prompt_ver(version: str)-> dict[str, str] | None:
    """

    :param version:
    :return:
    """

    prompt_version = {
        "v1":v1,
        "v2":v2
        }
    try:
        prompt = prompt_version[version]
        logger.info(f"ℹ️  Return Prompt version {version}")
        return prompt
    except Exception as e:
        logger.warning(f"️⚠️️ Prompt version {version} Not Found!!\n\n{e}")
        return None