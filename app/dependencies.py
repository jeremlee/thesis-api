from pydantic import BaseModel
from dotenv import load_dotenv
from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
import whisper
import os
from whisper.model import Whisper
from typing import Dict, Any

load_dotenv(".env.local")
configure(api_key=os.getenv("GEMINI_API_KEY"))

gemini_model = GenerativeModel("gemini-2.0-flash")
transcription_model: Whisper = whisper.load_model("base")

parsing_prompt = "dont give me anything aside from a json file which has the categories: name, city, contact number, email, educational background(with fields:degree,start_date,end_date,institution), soft skills, hard skills, work experience(with fields: title,company,start_date,end_date,description), and projects(with fields:name,start_date,end_date,description). parse this resume:"
extra_transcript_prompt = (
    "dont give me anything but a json with 4 fields(sentimental_analysis, personality_traits, communication_style_insights, interview_insights)"
    " giving me sentimental analysis and personality traits based on this interview transcript (each field detailed with at least 100 words). "
    "Detailed breakdown of personality traits such as openness, conscientiousness, extroversion, etc. Furthermore,"
    "giving me the break down of the communication styles (e.g., assertive, passive, empathetic) based on the interview transcript(at least 100 words)"
    "Furthermore, extract and display key insights from the interview, including sentiment, communication style, and soft skills.(100 words)."
    "Put them in their appropriate fields as mentioned above."
    "\nTranscript: "
)  # used in transcribe.py
scoring_prompt = "score the candidate from 1-5 (2 decimal places only) based on the resume and transcript, and sentimental analysis. Furthermore, also add a score from 1-100 the predictive success of the candidate, dont give me anything but a json with three fields: raw score, reason, and predictive_success"


class ExtraAnalysisData(BaseModel):  # result from transcribe API
    sentimental_analysis: str
    personality_traits: str
    communication_style_insights: str
    interview_insights: str


class ScoreInput(BaseModel):
    resume: str
    transcript: str
    extra_analysis: ExtraAnalysisData
