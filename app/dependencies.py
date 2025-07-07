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


class ScoreInput(BaseModel):
    resume: str
    transcript: str
