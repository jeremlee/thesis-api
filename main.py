from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
import whisper
import fitz
import os
import json
import re

load_dotenv(".env.local")
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
gemini_model = genai.GenerativeModel('gemini-2.0-flash')
transcription_model = whisper.load_model("base")
parsing_prompt = "dont give me anything aside from a json file which has the categories: name, city, contact number, email, educational background(with fields:degree,start_date,end_date,institution), soft skills, hard skills, work experience(with fields: title,company,start_date,end_date,description), and projects(with fields:name,start_date,end_date,description). parse this resume:"
sentiment_prompt = "dont give me anything but a string giving me sentimental analysis and personality traits based on this interview transcript (detailed with at least 100 words). Detailed breakdown of personality traits such as openness, conscientiousness, extroversion, etc.\nTranscript: "
scoring_prompt = "score the candidate from 1-10 based on the resume and transcript, dont give me anything but a json with two fields: raw score, and reason"
app = FastAPI()

class ScoreInput(BaseModel):
    resume: str
    transcript: str

@app.get("/")
def home():
    return {"message": "Hello"}

@app.post("/transcribe")
def transcribe(file_path: str):
    try:
        full_path = os.path.join("interviews", file_path) #adjust for database later
        if not os.path.exists(full_path):
            return {"error": "File not found."}
        result = transcription_model.transcribe(full_path)
        sentiment_analysis = gemini_model.generate_content(sentiment_prompt + result["text"])
        return {"transcription": result["text"], "sentiment_analysis": sentiment_analysis.text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/parseresume")
def parse_resume(file_path: str):
    try:
        full_path = os.path.join("resumes", file_path) #adjust for database later
        if not os.path.exists(full_path):
            return {"error": "File not found."}
        doc = fitz.open(full_path)
        text = ""
        for page in doc:
            text += page.get_text()
            
        response = gemini_model.generate_content(parsing_prompt + "\n" + text)
        raw_output = response.text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()
        return json.loads(raw_output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model output was not valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/score")
def score_candidate(data: ScoreInput):
    try:
        prompt = scoring_prompt + "\nResume: " + data.resume + "\nTranscript: " + data.transcript 
        response = gemini_model.generate_content(prompt)
        raw_output = response.text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()
        return json.loads(raw_output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model output was not valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


