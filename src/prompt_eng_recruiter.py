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
        Using the provided Job Description and Candidate Resume, draft two distinct 2-minute elevator pitches for the "Tell me about yourself" interview question.
        Goal: Prove the candidate is the ideal fit by weaving specific resume achievements into the requirements of the JD.
        Requirements:
            Pitch 1 (STAR Method): Focus on a high-impact "success story" narrative.
            Structure: Situation, Task, Action, Result.
            Pitch 2 (HERO Method): Focus on a value-proposition and leadership narrative.
            Structure: Headline (Who you are), Effect (The value you bring), Rationale (Why you do it), Operations (How you work).
        Tone: Professional, confident, and narrative-driven.
        Constraint: Ensure the spoken length for each is approximately 300 words (to fit the 2-minute limit).
    """,
    ## this prompt is going to ask the LLM to extract the Job Title and Company for the tracker
    "q_meta":"""
    Task: Extract the Company Name and the Job Title from the Job Description.
    Constraint: Output ONLY a valid JSON object. Do not include markdown formatting, backticks, or conversational text.
    If you cannot find the information, use "Unknown" as the value.
    
    Expected Format:
    {"company": "Extracted Company Name", "title": "Extracted Job Title"}
    """
}


# Define the Prompt, this tells the LLM how to behave
prompt_template = """
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

interview_system_prompt = """You are an expert technical recruiter and hiring manager interviewing a candidate for the {title} position at {company}.
        
        Strict Rules:
        1. Ask ONE question at a time. Never ask multiple questions in a single response.
        2. Wait for the candidate's answer before proceeding.
        3. Base your questions on standard behavioral (STAR method) and technical requirements for this type of role.
        4. Occasionally ask follow-up questions based on the candidate's previous answers to dig deeper.
        5. Maintain a professional, encouraging, but rigorous tone.
        6. Do NOT break character. Do not say "I am an AI".     


"""

# ---------- Functions --------------#
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