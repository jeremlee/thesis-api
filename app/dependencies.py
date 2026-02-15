from asyncio import Semaphore
import asyncio
from pydantic import BaseModel
from dotenv import load_dotenv
from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
import whisper
import json
from whisper.model import Whisper
from transformers import pipeline
import torch
from typing import Any
from app.executor import _executor
import re
from json import JSONDecoder, JSONDecodeError

from app.config import get_settings
from app.response_schemas.resume_format import resume_response_schema
from app.response_schemas.transcript_format import transcript_response_schema
from app.response_schemas.score_format import scoring_response_schema
from app.response_schemas.comparison_format import candidate_comparison_schema
from app.response_schemas.chatbot_format import chatbot_schema
from sentence_transformers import SentenceTransformer

load_dotenv(".env.local")
configure(api_key=get_settings().gemini_api_key)

GEMMA_PIPE: Any = None
GEMMA_SEMAPHORE: Semaphore = asyncio.Semaphore()


async def get_gemma_pipe():
    global GEMMA_PIPE
    if GEMMA_PIPE is not None:
        return GEMMA_PIPE

    def _initialize_pipe(device):
        return pipeline(
            "text-generation",
            model=gemma_path,
            tokenizer=gemma_path,
            device=device,
            dtype=torch.float16,
            max_new_tokens=700,
        )

    try:
        GEMMA_PIPE = await asyncio.get_running_loop().run_in_executor(
            _executor, lambda: _initialize_pipe(device=0)
        )
    except AssertionError:
        GEMMA_PIPE = await asyncio.get_running_loop().run_in_executor(
            _executor, lambda: _initialize_pipe(device=-1)
        )

    return GEMMA_PIPE


model_path = "all-mpnet-base-v2"

embedding_model = SentenceTransformer(model_path)

documents_to_index = [
    "Alliance Software, Inc. is a global IT services and solutions company. Alliance was established in 2000 and has since grown to become.",
    "Alliance Software's vision is to be the premier Filipino global IT services and solutions company known for our advanced technology, mature yet evolving process, the highest level of quality delivery and our commitment to exceed customer expectations.",
    "Alliance Software's mission is: we are committed to empower organizations and communities through innovative IT Solutions and Services.",
    "Alliance Software's president is Mr. Robert J. Cheng.",
    "Alliance Software Inc. has 505 employees as of March 2025.",
    "Alliance Software's business domains are IT services and IT solutions.",
    "Alliance Software has three offices: one in Cebu (established in April 2000), one in Manila (established in April 2002), and one in Tokyo (established in April 2006).",
    "Alliance Software Inc. is located in 14th Floor, Buildcomm Center, Sumilon Road, Cebu Business Park, Cebu City 6000, PH",
    "Alliance Software's core values are quality, agility, integrity, exceeding customer expectations through innovation, and efficiency",
    "Candidates are scored using AI by analyzing their resumes and self-introduction videos.",
    "Candidates are able to apply for jobs listed within the list.",
]


def extract_json_text(s: str) -> str | None:
    # try fenced ```json``` first (non-greedy)
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", s, re.S)
    if fenced:
        return fenced.group(1)

    # fallback: find first {...} that json.JSONDecoder can decode
    decoder = JSONDecoder()
    start = s.find("{")
    while start != -1:
        try:
            _, idx = decoder.raw_decode(s[start:])
            return s[start : start + idx]
        except JSONDecodeError:
            start = s.find("{", start + 1)
    return None

core_values = (
    # QUALITY + Attention to Detail
    "Quality and Excellence: A commitment to high standards, precision, and craftsmanship. "
    "Demonstrates meticulous attention to detail, thoroughness in work, and a drive to "
    "deliver error-free, polished results. "
    # AGILITY + Adaptability
    "Agility and Adaptability: The ability to pivot quickly and maintain performance in "
    "fast-paced, high-pressure, or ambiguous environments. A fast learner who embraces "
    "change and remains flexible when priorities shift. "
    # INTEGRITY + Accountability
    "Integrity and Accountability: Operating with ethical honesty, transparency, and "
    "strong moral principles. Taking full ownership of individual outcomes, admitting "
    "mistakes, and following through on all commitments and responsibilities. "
    # INNOVATION + Problem Solving
    "Innovation and Exceeding Expectations: A proactive growth mindset driven by "
    "curiosity, creative problem-solving, and resourcefulness. Consistently seeks "
    "to improve the status quo and provide value beyond the basic requirements. "
    # EFFICIENCY + Self-Management
    "Efficiency and Productivity: Exceptional time management, organizational skills, "
    "and a results-oriented focus. Capable of optimizing workflows, prioritizing "
    "effectively, and managing resources to hit deadlines without sacrificing quality. "
    # INTERPERSONAL + Soft Skills
    "Interpersonal Intelligence and Collaboration: Strong communication skills, "
    "active listening, and empathy. A team player who fosters synergy, manages "
    "conflicts constructively, and supports the growth of others through mentorship."
)

soft_skills_baseline = (
    # COMMUNICATION
    "Effective Communication: The ability to articulate ideas clearly and concisely. "
    "Expertise in active listening, stakeholder management, and tailoring "
    "complex information for different audiences. "
    
    # EMOTIONAL INTELLIGENCE
    "Emotional Intelligence (EQ): High self-awareness and social awareness. "
    "Demonstrates empathy, manages personal triggers, and reads social cues "
    "effectively to build trust and maintain positive relationships. "
    
    # CRITICAL THINKING
    "Critical Thinking and Reasoning: Logical approach to decision-making. "
    "Capable of analyzing data, identifying biases, and connecting dots between "
    "disparate pieces of information to reach a sound conclusion. "
    
    # CONFLICT RESOLUTION
    "Conflict Management: Navigating disagreements with diplomacy. "
    "Focused on win-win solutions, de-escalating tension, and maintaining "
    "professionalism during difficult conversations or high-stress periods. "
    
    # LEADERSHIP & INFLUENCE
    "Influence and Leadership: Even without a formal title, the ability to "
    "motivate others, delegate tasks effectively, and drive consensus "
    "around shared goals. "
    
    # RESILIENCE & GRIT
    "Mental Resilience: Maintaining a positive and productive attitude in the "
    "face of rejection, failure, or heavy workloads. Shows persistence and "
    "emotional stability under pressure."
)

falcon_path = "falcon-3b-instruct"
gemma_path = "gemma-3-1b-it"

parsing_gemini_model = GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": resume_response_schema,
    },
)
transcript_gemini_model = GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": transcript_response_schema,
    },
)
scoring_gemini_model = GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": scoring_response_schema,
    },
)

transcription_model: Whisper = whisper.load_model("base")

comparing_gemini_model = GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": candidate_comparison_schema,
    },
)

chatbot_gemini_model = GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": chatbot_schema,
    },
)


localized_parsing_prompt = (
    """
You are an expert resume parser. Your task is to extract all the key information from the resume provided below and format it into a single JSON object.

You must follow these rules strictly:
1. **Do not include any text before or after the JSON object.** The response must start with `{` and end with `}`.
2. **Do not add any additional fields or information not specified in the schema.**
3. **If a field's information is not present in the resume, use `null` for that field's value.**
4. **Adhere strictly to the JSON schema provided below.**"""
    + "\n###JSON schema:\n"
    + json.dumps(resume_response_schema, ensure_ascii=False)
    + "\n###Resume Text to Parse: \n"
)

localized_transcription_prompt = f"""
You are an expert HR analyst and behavioral psychologist. Your task is to analyze the given text (such as a resume, personal statement, or writing sample) and extract deeper insights in JSON format.

You must follow these rules strictly:
1. **Do not include any text before or after the JSON object.** The response must start with `{{` and end with `}}`.
2. **Adhere exactly to the JSON schema provided below.**
3. **If a field’s information cannot be inferred confidently, use `null`.**
4. **Keep responses concise but insightful.**
5. **Focus on the tone, phrasing, and implied characteristics of the text.**
6. **For cultural fit insights, base it on these core values:** {core_values}

### JSON schema:
{json.dumps(transcript_response_schema, ensure_ascii=False)}
### Text to Analyze:
"""

localized_scoring_prompt = (
    """
You are an expert HR evaluator.
You must output ONLY a JSON object.

Your task is to produce EXACTLY ONE valid JSON object that conforms strictly to the provided JSON schema.

ABSOLUTE RULES (NON-NEGOTIABLE):
1. Output MUST be valid JSON.
2. Output MUST start with `{` and end with `}`.
3. Output MUST contain ONLY the JSON object — no explanations, no labels, no markdown, no backticks.
4. Use ONLY double quotes (`"`). Single quotes (`'`) are forbidden.
6. Do NOT include field names as headings (e.g., "Predictive Success:").
7. Do NOT include comments, trailing commas, or extra whitespace outside the JSON object.

SCHEMA COMPLIANCE RULES:
1. Do NOT add, remove, or rename fields.
2. ALL fields in the schema are required.
3. If information is missing or cannot be inferred, set the value to null.
4. Follow field constraints exactly:
   - "reason": at least 100 words
   - "phrases": array of short phrases, each no more than 5 words summarizing the reason
   - "skill_gaps_recommendations": no more than 50 words

FIELD CONSTRAINTS (MANDATORY):
- `reason`: at least 100 words
- `phrases`: array of short phrases, each no more than 5 words
- `skill_gaps_recommendations`: at most 50 words

Adhere strictly to the JSON schema below.
"""
    + "\n### JSON Schema:\n"
    + json.dumps(scoring_response_schema, ensure_ascii=False)
    + "\n### Text to Analyze:\n"
)

chatbot_prompt = (
    """
You are a knowledgeable and precise chatbot assistant. Your task is to answer the user's question using ONLY the provided retrieved context.
Respond only with a valid JSON object. Ignore any extra text you want to include.

You must follow these rules strictly:
1. **Do not include any text before or after the JSON object.** The response must start with `{` and end with `}`.
2. **Do not add any additional fields or keys not specified in the schema.**
3. **If the answer cannot be found in the provided context, respond with a concise, honest reply indicating that the information is not available.**
4. **Adhere strictly to the JSON schema provided below.**
5. **The value of `reply` must be between 5 and 100 words.**

"""
    + "\n### JSON Schema:\n"
    + json.dumps(chatbot_schema, ensure_ascii=False)
    + "\n\n### Retrieved Context:\n"
    + "{context}"
    + "\n\n### User Question:\n"
    + "{question}\n"
)



localized_comparison_prompt = (
    """
You are an expert HR evaluator. Your task is to compare two candidates based on their resumes and transcript results and produce a single JSON object that strictly follows the schema provided.

You must follow these rules strictly:
1. **Do not include any text before or after the JSON object.** The response must start with `{` and end with `}`.
2. **Do not add any additional fields or information not specified in the schema.**
3. **All fields in the schema are required.** If information is missing, use `null`.
4. **Follow the field constraints exactly:**
   - `better_candidate` must be the exact name of the candidate. Put the actual name of the candidate.
   - `reason` must be between **50 and 100 words**.
   - Each item in `highlights` must be a **short key phrase of no more than 10 words**.
5. **Adhere strictly to the JSON schema provided below.**
6. **Your final output MUST be valid JSON. No comments. No trailing commas.**

"""
    + "\n###JSON schema:\n"
    + json.dumps(candidate_comparison_schema, ensure_ascii=False)
    + "\n###Text to Analyze:\n"
)

# deprecated
parsing_prompt = "dont give me anything aside from a json file which has the categories: name, city, contact number, email, educational background(with fields:degree,start_date,end_date,institution), soft skills, hard skills, work experience(with fields: title,company,start_date,end_date,description), and projects(with fields:name,start_date,end_date,description). parse this resume:"
extra_transcript_prompt = (
    "dont give me anything but a json with 5 fields(sentimental_analysis, personality_traits, communication_style_insights, interview_insights, cultural_fit_insights)"
    " giving me sentimental analysis and personality traits based on this interview transcript (each field detailed with at least 100 words). "
    "Detailed breakdown of personality traits such as openness, conscientiousness, extroversion, etc. Furthermore,"
    "giving me the break down of the communication styles (e.g., assertive, passive, empathetic) based on the interview transcript(at least 100 words)"
    "Furthermore, extract and display key insights from the interview, including sentiment, communication style, and soft skills.(100 words)."
    "Furthermore, also give cultural fit insights (no more than 25 words) comparing the candidate's values to these values: "
    + core_values
    + " "
    "Put them in their appropriate fields as mentioned above."
    "\nTranscript: "
)  # used in transcribe.py
# deprecated
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
