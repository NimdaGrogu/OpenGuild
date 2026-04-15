
from __future__ import annotations

import io
import logging
import os

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from openai import OpenAI

from prompts.prompts import interview_eval_prompt, interview_system_prompt

logger = logging.getLogger("interview_service")


class MockInterviewEngine:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def transcribe_audio(self, audio_bytes: bytes) -> str | None:
        """
        Transcribe raw audio bytes using OpenAI Whisper.
        """
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
            )
            return transcript
        except Exception as exc:
            logger.error("Audio transcription failed: %s", exc)
            return None

    def generate_tts(self, text: str) -> bytes | None:
        """
        Generate speech audio from text using OpenAI TTS.
        """
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=text,
            )
            return response.content
        except Exception as exc:
            logger.error("Text-to-speech failed: %s", exc)
            return None

    def evaluation_report(
        self,
        title: str,
        company: str,
        transcript: str,
        evaluation_report: str,
    ) -> str:
        """
        Generate the final interview feedback report.
        """
        eval_prompt = ChatPromptTemplate.from_template(interview_eval_prompt)

        feedback = (eval_prompt | self.llm).invoke(
            {
                "title": title,
                "company": company,
                "transcript": transcript,
                "evaluation_report": evaluation_report,
            }
        )

        return feedback.content

    def chat_interview(
        self,
        title: str,
        company: str,
        candidate_report: str,
        history,
        user_input: str,
    ) -> str:
        """
        Generate the next interviewer response in the interview flow.
        """
        system_prompt = interview_system_prompt.format(
            title=title,
            company=company,
            candidate_report=candidate_report,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        response = (prompt | self.llm).invoke(
            {
                "history": history,
                "input": user_input,
            }
        )

        return response.content