from pydantic import BaseModel
from dotenv import load_dotenv
from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
from app.response_schemas.resume_format import resume_response_schema
from app.response_schemas.transcript_format import transcript_response_schema
from app.response_schemas.score_format import scoring_response_schema
import whisper
import os
from whisper.model import Whisper

load_dotenv(".env.local")
configure(api_key=os.getenv("GEMINI_API_KEY"))

core_values = "quality, agility, integrity, exceeding customer expectations through innovation, efficiency"
falcon_path = "D:\\Documents\\A_College\\falcon-3b-instruct"
gemma_path = "D:\\Documents\\A_College\\gemma-3-1b-it"
parsing_gemini_model = GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": resume_response_schema,
    },
)
transcript_gemini_model = GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": transcript_response_schema,
    },
)
scoring_gemini_model = GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": scoring_response_schema,
    },
)
transcription_model: Whisper = whisper.load_model("base")


localized_parsing_prompt = """

You are an expert resume parser. Your task is to extract all the key information from the resume provided below and format it into a single JSON object.

You must follow these rules strictly:
1. **Do not include any text before or after the JSON object.** The response must start with `{` and end with `}`.
2. **Do not add any additional fields or information not specified in the schema.**
3. **If a field's information is not present in the resume, use `null` for that field's value.**
4. **Adhere strictly to the JSON schema provided below.**""" + "\n###JSON schema:\n" + resume_response_schema + "\n###Resume Text to Parse: \n"

localized_transcription_prompt = """

You are an expert HR analyst and behavioral psychologist. Your task is to analyze the given text (such as a resume, personal statement, or writing sample) and extract deeper insights in JSON format.

You must follow these rules strictly:
1. **Do not include any text before or after the JSON object.** The response must start with `{` and end with `}`.
2. **Adhere exactly to the JSON schema provided below.**
3. **If a field’s information cannot be inferred confidently, use `null`.**
4. **Keep responses concise but insightful.**
5. **Focus on the tone, phrasing, and implied characteristics of the text.**
""" + "\n###JSON schema:\n" + transcript_response_schema + "\n###Text to Analyze: \n"

localized_scoring_prompt = """

You are an expert HR evaluator. Your task is to assess the candidate based on their resume and transcript results and provide a detailed evaluation in a single JSON object.

You must follow these rules strictly:
1. **Do not include any text before or after the JSON object.** The response must start with `{` and end with `}`.
2. **Do not add any additional fields or information not specified in the schema.**
3. **All fields in the schema are required.** If information is missing, use `null`.
4. **Follow the field constraints exactly:** 
   - `raw_score` must be a number with exactly two decimal places (1.00-5.00)
   - `reason` must be at least 100 words
   - `predictive_success` must be an integer between 1 and 100
   - `phrases` must be key phrases no longer than 5 words each
   - `skill_gaps_recommendations` must be at most 50 words
5. **Adhere strictly to the JSON schema provided below.**

""" + "\n###JSON schema:\n" + scoring_response_schema + "\n###Text to Analyze: \n"


parsing_prompt = "dont give me anything aside from a json file which has the categories: name, city, contact number, email, educational background(with fields:degree,start_date,end_date,institution), soft skills, hard skills, work experience(with fields: title,company,start_date,end_date,description), and projects(with fields:name,start_date,end_date,description). parse this resume:"
extra_transcript_prompt = (
    "dont give me anything but a json with 5 fields(sentimental_analysis, personality_traits, communication_style_insights, interview_insights, cultural_fit_insights)"
    " giving me sentimental analysis and personality traits based on this interview transcript (each field detailed with at least 100 words). "
    "Detailed breakdown of personality traits such as openness, conscientiousness, extroversion, etc. Furthermore,"
    "giving me the break down of the communication styles (e.g., assertive, passive, empathetic) based on the interview transcript(at least 100 words)"
    "Furthermore, extract and display key insights from the interview, including sentiment, communication style, and soft skills.(100 words)."
    "Furthermore, also give cultural fit insights (no more than 25 words) comparing the candidate's values to these values: " + core_values + " "
    "Put them in their appropriate fields as mentioned above."
    "\nTranscript: "
)  # used in transcribe.py
scoring_prompt = (
    "output only a json with 6 fields: raw_score (from 1-5), reason (at least 100 words), phrases (each no more than 5 words), summary (no more than 20 words), predictive_success (1-100), and skill_gaps_recommendations. The raw_score field is the candidate's score based on how fit for the role he is and based on"
    " the resume, the transcript, and the other extra analyses. The reason is the reason justifying the raw_score."
    " The summary is the summary of the reason which must not exceed 20 words."
    " The phrases is a field with its own field named 'phrase' (no more than 5 words), which serve as easy-to-read summaries of the reason why the candidate's score is like this."
    " Meanwhile, the predictive_success field is the number between 1-100 which tells us how successful the candidate might be."
    "Furthermore, in the skill_gaps_recommendations part, highlight any skill gaps in the candidate, along with recommendations for training or development. (at most 50 words only)"
)


class ExtraAnalysisData(BaseModel):  # result from transcribe API
    sentimental_analysis: str
    personality_traits: str
    communication_style_insights: str
    interview_insights: str
    cultural_fit_insights: str
