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
scoring_prompt = "output only a json with 3 fields: raw_score (from 1-5), reason (at least 100 words), and predictive_success (1-100). The raw_score field is the candidate's score based on how fit for the role he is and based on" \
                    " the resume, the transcript, and the other extra analyses. The reason is the reason justifying the raw_score." \
                    " Meanwhile, the predictive_success field is the number between 1-100 which tells us how successful the candidate might be."


class ExtraAnalysisData(BaseModel):  # result from transcribe API
    sentimental_analysis: str
    personality_traits: str
    communication_style_insights: str
    interview_insights: str


class ScoreInput(BaseModel):
    resume: str
    transcript: str
    role : str
    extra_analysis: ExtraAnalysisData
