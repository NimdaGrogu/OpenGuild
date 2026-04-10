# 🚀 OpenGuild: AI Job Hunt Assistant

![openguild.png](openguild.png)   

An intelligent, dual-purpose application designed to optimize the job search process. OpenGuild combines a **RAG-powered Resume Analyzer** to evaluate candidate fit, an integrated **Job Application Tracker** to manage the hiring pipeline, and a **Voice-Driven AI Mock Interviewer** to help you prep for the big day.

Built with Python, Streamlit, LangChain, FAISS, and OpenAI, and fully containerized with Docker.

---

## 🏗️ Architecture 

![job_hunt_arch1.png](job_hunt_arch1.png)
*(Note: Ensure your architecture images are uploaded to your repo to display correctly)*

---

## ✨ Key Features

### 🔍 1. AI Resume Analyzer
* **Semantic Match Scoring:** Uses vector embeddings (FAISS) to calculate a 0-100% quantitative fit score based on hard skills, experience, and industry context.
* **Smart PDF Parsing:** Implements layout-aware document chunking using PyMuPDF and pdfplumber to accurately read complex, multi-column resumes without losing context.
* **Comprehensive SWOT Analysis:** Automatically generates Strengths, Weaknesses, Opportunities, and Threats for the candidate relative to the specific role.
* **Elevate Speech & Application Kit:** Drafts a tailored cover letter and helps you structure answers using industry frameworks like **STAR** (Situation, Task, Action, Result) and **HERO** (Headline, Effect, Rationale, Operation).
* **Exportable Reports:** Download the full analysis as a formatted Markdown file.

### 📊 2. Job Application Tracker
* **Seamless Integration:** One-click save from the Analyzer directly to your Tracker, auto-extracting the Company Name and Job Title using structured LLM outputs.
* **Visual Dashboard:** Real-time metrics and charts displaying pipeline health, interview statuses, and application momentum over time.
* **Interactive Data Editor:** Update application statuses (e.g., "Applied" -> "Interviewing") directly within the UI.
* **Persistent Storage:** Data is saved locally via CSV, ensuring your pipeline survives container restarts.

### 🎙️ 3. Voice-Driven Mock Interview (NEW!)
* **Practice Under Pressure:** Do a live audio interview with your AI Coach and get real-time evaluations on your delivery.
* **Tailored to the Role:** The AI automatically adopts the persona of the hiring manager for the specific job and company you saved in your tracker.
* **Speech-to-Text & Neural Voice:** Speak naturally into your microphone. The AI transcribes your answer, processes it, and speaks back to you in a realistic neural voice.
* **Performance Report:** Get personalized, expert feedback highlighting where you did well and where you can improve before the real interview.

---

## 🛠️ Technology Stack

* **Frontend:** Streamlit
* **AI & Orchestration:** LangChain Core, OpenAI API (`gpt-4o`)
* **Audio Processing:** OpenAI Whisper (STT) and TTS-1 (Text-to-Speech)
* **Vector Database:** FAISS (Local)
* **Data Processing:** Pandas, PyMuPDF, pdfplumber
* **Deployment:** Docker & Docker Compose

---

## 🚀 Getting Started

### Prerequisites
* Python 3.13+ (for local development)
* Docker and Docker Compose (for containerized deployment)
* An active [OpenAI API Key](https://platform.openai.com/)

> **⚠️ Security Note:** Never commit your `.env` file to GitHub. It is already included in the `.gitignore`.

---

## 💻 How to Run Locally

### 1. Clone the Repository
```bash
git clone [https://github.com/NimdaGrogu/job-hunt-assistant.git](https://github.com/NimdaGrogu/job-hunt-assistant.git)
cd job-hunt-assistant
touch src/job_tracker.csv
```

### 2. Configure Environment Variables
Create a file named .env in the src/ folder (or project root) and add your keys:

```Bash
OPENAI_API_KEY=sk-your-actual-api-key-here
VERBOSE_RAG_LOGS=false 
```
(Note: When VERBOSE_RAG_LOGS=true, detailed LangChain callbacks will print in the terminal for debugging).

### 3. Install Dependencies
```Bash
pip install --upgrade pip
pip install -r requirements.txt
```
### 4. Run the App
```Bash
streamlit run src/app.py
```
The app should open automatically at http://localhost:8501

### 🐳 How to Run with Docker
## Option A: Standard Docker Run
Build the Image:

```Bash
docker build -t openguild .
```
Run the Container (Passes your local .env file securely):

```Bash
docker run -p 8501:8501 --env-file src/.env openguild
```
## Option B: Docker Compose (Recommended)

Assuming you are in the root directory and your .env is configured:

```Bash
docker compose up -d
```
Access the app by opening your browser to http://localhost:8501


## 🤝 Roadmap & Upcoming Features
⚖️ LLM as Judge (WIP): Integrating the Gemini API to act as a secondary guardrail, ensuring fair and unbiased evaluation of candidates regardless of background, ethnicity, or socio-economic position.

## 🤝 Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

# 📄 License
MIT