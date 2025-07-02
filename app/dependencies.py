from pydantic import BaseModel
from dotenv import load_dotenv
from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
import whisper
import os
from whisper.model import Whisper

load_dotenv(".env.local")
configure(api_key=os.getenv("GEMINI_API_KEY"))

gemini_model = GenerativeModel("gemini-2.0-flash")
transcription_model: Whisper = whisper.load_model("base")

parsing_prompt = "dont give me anything aside from a json file which has the categories: name, city, contact number, email, educational background(with fields:degree,start_date,end_date,institution), soft skills, hard skills, work experience(with fields: title,company,start_date,end_date,description), and projects(with fields:name,start_date,end_date,description). parse this resume:"
sentiment_prompt = "dont give me anything but a string giving me sentimental analysis and personality traits based on this interview transcript (detailed with at least 100 words). Detailed breakdown of personality traits such as openness, conscientiousness, extroversion, etc.\nTranscript: "
scoring_prompt = "score the candidate from 1-10 based on the resume and transcript, dont give me anything but a json with two fields: raw score, and reason"


class ScoreInput(BaseModel):
    resume: str
    transcript: str
