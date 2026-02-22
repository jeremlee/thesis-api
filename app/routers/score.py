import asyncio
import io
import json
import re

import numpy as np
import PyPDF2
import requests
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity
import time
from app.dependencies import (
    core_values,
    embedding_model,
    extra_transcript_prompt,
    localized_scoring_prompt,
    parsing_gemini_model,
    parsing_prompt,
    scoring_gemini_model,
    soft_skills_baseline,
    transcript_gemini_model,
    transcription_model,
)
from app.executor import _executor
from app.response_schemas.score_format import ScoreCandidateResponse
from app.services.cloudinary_service import fetch_file, generate_signed_url
from app.services.mongodb_service import mongodb
from app.services.supabase_service import get_supabase_admin_client

router = APIRouter(prefix="/score", tags=["Score"])


class JobFitData(BaseModel):
    hard_skills: str
    work_experiences: str
    projects: str


class PredictiveSuccessData(BaseModel):
    soft_skills: str
    transcription: str


def get_job_fit_data(resume_json: dict) -> JobFitData:

    hard_skills = ""
    if "hard_skills" in resume_json:
        hard_skills = "Technical Competencies: " + ", ".join(resume_json["hard_skills"])

    work_experiences = ""
    if "work_experience" in resume_json:
        exp_parts = [
            f"Role: {e.get('title')} at {e.get('company')}. Responsibilities and Tech: {e.get('description', '')}"
            for e in resume_json["work_experience"]
        ]
        work_experiences = "\n".join(exp_parts)

    projects = ""
    if "projects" in resume_json:
        proj_parts = [
            f"Project: {p.get('name')}. Details: {p.get('description', '')}"
            for p in resume_json["projects"]
        ]
        projects = "\n".join(proj_parts)

    return JobFitData(
        hard_skills=hard_skills, work_experiences=work_experiences, projects=projects
    )


def get_predictive_success_data(
    resume_json: dict, transcription_data: str
) -> PredictiveSuccessData:
    soft_skills = ""
    if "soft_skills" in resume_json:
        soft_skills = "Behavioral Competencies: " + ", ".join(
            resume_json["soft_skills"]
        )

    return PredictiveSuccessData(
        soft_skills=soft_skills, transcription=transcription_data
    )


# Convert ObjectId to string for JSON serialization from MongoDB
def convert_objectid(obj: dict) -> dict:
    """Convert ObjectId instances to strings. Always returns a dict."""
    return {k: _convert_value(v) for k, v in obj.items()}


def _convert_value(obj):
    """Helper to convert individual values."""
    match obj:
        case ObjectId():
            return str(obj)
        case dict():
            return {k: _convert_value(v) for k, v in obj.items()}
        case list():
            return [_convert_value(item) for item in obj]
        case None:
            return None
    # Convert numpy scalars (np.float32, np.float64, np.int64, etc.) to Python native
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def extract_json_payload(text: str) -> dict:
    cleaned = text.replace("```json", "").replace("```", "")
    cleaned = cleaned.replace("“", '"').replace("”", '"').strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise ValueError("No JSON object found")
        return json.loads(match.group())


async def extract_text_from_pdf_url(pdf_url: str) -> str:
    def _extract_text() -> str:
        text = ""
        for page in PyPDF2.PdfReader(
            io.BytesIO(requests.get(pdf_url, timeout=30).content)
        ).pages:
            text += (page.extract_text() or "") + "\n"
        output = text.strip()
        if not output:
            raise ValueError("No text could be extracted from the PDF.")
        return output

    return await asyncio.get_running_loop().run_in_executor(_executor, _extract_text)


async def ensure_parsed_resume(
    applicant_id: str, resume_public_id: str, supabase_client
) -> dict:
    file = await fetch_file(resume_public_id)
    resource_type = file.get("resource_type", "raw") if file else "raw"
    pdf_url = generate_signed_url(resume_public_id, resource_type)
    if not pdf_url:
        raise HTTPException(status_code=400, detail="Resume file URL not found")

    text = await extract_text_from_pdf_url(pdf_url)

    raw_output = await asyncio.get_running_loop().run_in_executor(
        _executor,
        lambda: parsing_gemini_model.generate_content(
            parsing_prompt + "\n" + text
        ).text.strip(),
    )
    parsed_output = extract_json_payload(raw_output)

    inserted_id = await mongodb.insert_document(
        "parsed_resume",
        {"applicant_id": applicant_id, "raw_output": parsed_output},
    )
    if not inserted_id:
        raise HTTPException(status_code=500, detail="Failed to insert parsed resume")

    await asyncio.get_running_loop().run_in_executor(
        _executor,
        lambda: (
            supabase_client.table("applicants")
            .update({"parsed_resume_id": str(inserted_id)})
            .eq("id", applicant_id)
            .execute()
        ),
    )

    return {
        "_id": inserted_id,
        "applicant_id": applicant_id,
        "raw_output": parsed_output,
    }


async def ensure_transcription(
    applicant_id: str, video_public_id: str, supabase_client
) -> dict:
    video_metadata = await fetch_file(video_public_id, resource_type="video")
    if not video_metadata:
        raise HTTPException(status_code=400, detail="Video file URL not found")

    video_url = video_metadata.get("secure_url") or video_metadata.get("url")
    if not video_url:
        raise HTTPException(status_code=400, detail="Video URL not found")

    transcript_result = await asyncio.get_running_loop().run_in_executor(
        _executor, lambda: transcription_model.transcribe(video_url)
    )

    extra_analysis_text = await asyncio.get_running_loop().run_in_executor(
        _executor,
        lambda: transcript_gemini_model.generate_content(
            f"{extra_transcript_prompt}{transcript_result['text']}"
        ).text.strip(),
    )
    extra_analysis_data = extract_json_payload(extra_analysis_text)

    payload = {"transcription": transcript_result["text"]}
    payload.update(extra_analysis_data)

    inserted_id = await mongodb.insert_document(
        "transcribed",
        {"applicant_id": applicant_id, "transcription": payload},
    )
    if not inserted_id:
        raise HTTPException(status_code=500, detail="Failed to insert transcription")

    await asyncio.get_running_loop().run_in_executor(
        _executor,
        lambda: (
            supabase_client.table("applicants")
            .update({"transcribed_id": str(inserted_id)})
            .eq("id", applicant_id)
            .execute()
        ),
    )

    return {"_id": inserted_id, "applicant_id": applicant_id, "transcription": payload}


@router.post("/")
async def score_candidate(
    job_id: str = Query(..., description="Job ID"),
    applicant_id: str = Query(..., description="Applicant ID"),
    # This can be obtained from the database through applicant_id but instead moved the responsibility to NextJS to reduce latency of fetching from database
    resume_public_id: str = Query(
        ..., description="Cloudinary public_id of resume PDF."
    ),
    # This can be obtained from the database through applicant_id but instead moved the responsibility to NextJS to reduce latency of fetching from database
    transcript_public_id: str = Query(
        ..., description="Cloudinary public_id of transcript video"
    ),
) -> ScoreCandidateResponse:
    supabase_client = get_supabase_admin_client()
    try:
        job_listing_data = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: (
                supabase_client.table("job_listings")
                .select("title")
                .eq("id", job_id)
                .single()
                .execute()
            ),
        )

        if not getattr(job_listing_data, "data", None):
            raise HTTPException(status_code=404, detail="Job listing not found")

        parsed_resume, transcribed = await asyncio.gather(
            ensure_parsed_resume(applicant_id, resume_public_id, supabase_client),
            ensure_transcription(applicant_id, transcript_public_id, supabase_client),
        )

        if not transcribed:
            transcribed = {
                "transcription": {
                    "transcription": "No transcription available",
                    "sentimental_analysis": "No sentimental analysis found",
                    "personality_traits": "No personality traits found",
                    "communication_style_insights": "No communication style insights found",
                    "interview_insights": "No interview insights found",
                }
            }

        tags_response = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: (
                supabase_client.table("job_tags")
                .select("*, tags(*)")
                .eq("joblisting_id", job_id)
                .execute()
            ),
        )

        requirements_response = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: (
                supabase_client.table("jl_requirements")
                .select("requirement")
                .eq("joblisting_id", job_id)
                .execute()
            ),
        )

        tags_data = tags_response.data or []
        req_data = requirements_response.data or []

        tag_list = [
            t["tags"]["name"]
            for t in tags_data
            if t.get("tags") and t["tags"].get("name")
        ]
        tags_text = "Tags: " + ", ".join(tag_list)

        requirements_list = [r["requirement"] for r in req_data if r.get("requirement")]
        requirements_text = "Requirements: " + "; ".join(requirements_list)

        tags = [str(name) for name in tag_list]

        resume_json = parsed_resume["raw_output"]
        transcription = transcribed["transcription"]
        transcription_text = " ".join(str(v) for v in transcription.values())
        job_fit_data: JobFitData = get_job_fit_data(resume_json)
        predictive_success_data: PredictiveSuccessData = get_predictive_success_data(
            resume_json, transcription_text
        )

        # converts hard skills, work experiences, projects to numerical vector
        job_fit_text = (
            f"TECHNICAL SKILLS:\n{job_fit_data.hard_skills}\n\n"
            f"PROFESSIONAL EXPERIENCE:\n{job_fit_data.work_experiences}\n\n"
            f"TECHNICAL PROJECTS:\n{job_fit_data.projects}"
        )
        job_fit_embedding = embedding_model.encode(
            job_fit_text, normalize_embeddings=True
        )

        # converts soft skills to numerical vector
        soft_skills_text = f"SOFT SKILLS:\n{predictive_success_data.soft_skills}\n\n"
        soft_skills_embedding = embedding_model.encode(
            soft_skills_text, normalize_embeddings=True
        )
        # converts transcription to numerical vector
        transcription_text = (
            f"TRANSCRIPTION:\n{predictive_success_data.transcription}\n\n"
        )
        transcription_emb = embedding_model.encode(
            transcription_text, normalize_embeddings=True
        )
        # converts job requirements text and tags to numerical vector
        job_emb = embedding_model.encode(
            requirements_text + "\n" + tags_text, normalize_embeddings=True
        )
        # converts the company's core values to numerical vector
        cultural_fit_emb = embedding_model.encode(
            core_values, normalize_embeddings=True
        )
        soft_skills_baseline_emb = embedding_model.encode(
            soft_skills_baseline, normalize_embeddings=True
        )
        # THE NUMERICAL VECTORS WILL BE USED TO COMPUTE THE SCORES THROUGH COSINE SIMILARITY

        # computes the cosine similarity between the job_fit_data (hard skills, work experiences and projects) and the job requirements

        # take note that job_fit_score was previously referred to as raw_score

        job_fit_score = float(cosine_similarity([job_fit_embedding], [job_emb])[0][0])

        # computes the cosine similarity between the soft skills and the soft skills standard

        soft_skills_score = float(
            cosine_similarity([soft_skills_embedding], [soft_skills_baseline_emb])[0][0]
        )

        # computes the cosine similarity between the transcription data and the soft skills standard

        transcription_score = float(
            cosine_similarity([transcription_emb], [soft_skills_baseline_emb])[0][0]
        )

        # computes the cosine similarity between the soft skills and the cultural fit

        cultural_fit_score = float(
            cosine_similarity([soft_skills_embedding], [cultural_fit_emb])[0][0]
        )

        # computes the cosine similarity between the transcription data and the cultural fit

        transcription_cultural_fit_score = float(
            cosine_similarity([transcription_emb], [cultural_fit_emb])[0][0]
        )

        # 1. Calculate the Behavioral Blend (The "How they work" side)

        # We prioritize the transcription (interview) over the resume list
        behavioral_blend = (
            (transcription_cultural_fit_score * 0.30)
            + (transcription_score * 0.25)
            + (cultural_fit_score * 0.15)
            + (soft_skills_score * 0.30)
        )

        # normalizing values
        # will be stored in raw_output
        soft_skills_score_pct = min(100, int((soft_skills_score / 0.85) * 100))
        transcription_score_pct = min(100, int((transcription_score / 0.85) * 100))
        cultural_fit_score_pct = min(100, int((cultural_fit_score / 0.85) * 100))
        trans_cultural_fit_score_pct = min(
            100, int((transcription_cultural_fit_score / 0.85) * 100)
        )

        # 2. Calculate Final Predictive Success (50% Job Fit + 50% Behavior)

        # This results in a value between 0.0 and 1.0

        predictive_success_raw = (job_fit_score * 0.40) + (behavioral_blend * 0.60)

        # 3. Scaling for Human Readability

        # Since MPNet scores rarely hit 1.0, we scale the result.

        # A raw score of 0.80 should probably look like a 95% to a recruiter.

        predictive_success_final_score = min(
            100, int((predictive_success_raw / 0.85) * 100)
        )

        # 4. Job Fit Score (1-5 Star Rating)

        # Similarly, we scale 0.85 similarity to be a 5-star result. 0.85 is the perfect score
        job_fit_final_score = min(100, int((job_fit_score / 0.85) * 100))
        job_fit_stars = float(round(min(5.0, (job_fit_score / 0.85) * 5), 1))

        """
        scores are based from:
        job fit score (previously raw_score) = hard skills from resume, work experiences, projects
        predictive success = soft skills from resume, transcription, cultural fit
        """

        # PROMPT SECTION
        prompt = (
            localized_scoring_prompt
            + "\n Job: "
            + str(job_listing_data.data.get("title", "No title found"))
            + "\nResume: "
            + str(parsed_resume.get("raw_output", "No resume data found"))
            + "\nJob Tags: "
            + ", ".join(tags)
            + "\nTranscript: "
            + str(
                transcribed.get("transcription", {}).get(
                    "transcription", "No transcription data found"
                )
            )
            + "\n--- Candidate Analysis ---"
            + "\nSentimental Analysis: "
            + str(
                transcribed.get("transcription", {}).get(
                    "sentimental_analysis", "No sentimental analysis found"
                )
            )
            + "\nPersonality Traits: "
            + str(
                transcribed.get("transcription", {}).get(
                    "personality_traits", "No personality traits found"
                )
            )
            + "\nCommunication Style Insights: "
            + str(
                transcribed.get("transcription", {}).get(
                    "communication_style_insights",
                    "No communication style insights found",
                )
            )
            + "\nInterview Insights: "
            + str(
                transcribed.get("transcription", {}).get(
                    "interview_insights", "No interview insights found"
                )
            )
            + "CALCULATED SCORES BY COSINE SIMILARITY: \n"
            + f"JOB_FIT_SCORE = {job_fit_final_score}\n"
            + f"PREDICTIVE_SUCCESS_SCORE = {predictive_success_final_score}"
        )

        start_time = time.perf_counter()
        raw_output = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: scoring_gemini_model.generate_content(prompt).text.strip(),
        )
        end_time = time.perf_counter()
        duration = end_time - start_time  # Seconds
        raw_output = extract_json_payload(raw_output)

        # use these for success likelihood "visualization"
        raw_output["soft_skills_score"] = soft_skills_score_pct
        raw_output["transcription_score"] = transcription_score_pct
        raw_output["transcription_cultural_fit_score"] = trans_cultural_fit_score_pct
        raw_output["cultural_fit_score"] = cultural_fit_score_pct

        # response time
        raw_output["response_time"] = round(duration, 2)

        # adding the scores to the field
        # final scores
        raw_output["predictive_success"] = predictive_success_final_score
        raw_output["job_fit_score"] = job_fit_final_score
        raw_output["job_fit_stars"] = job_fit_stars

        # Ensure BSON-safe payload (ObjectId/numpy scalars/nested structures)
        raw_output = _convert_value(raw_output)

        # Ensure raw_output is a dict before passing to convert_objectid
        if not isinstance(raw_output, dict):
            raise HTTPException(status_code=500, detail="Invalid score data format")

        inserted_id = await mongodb.insert_document(
            "scored_candidates",
            {
                "applicant_id": applicant_id,
                "job_id": job_id,
                "score_data": raw_output,
                "created_at": time.time(),
            },
        )

        if not inserted_id:
            await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: (
                    supabase_client.table("applicants")
                    .delete()
                    .eq("id", applicant_id)
                    .execute()
                ),
            )
            raise HTTPException(status_code=500, detail="Failed to insert score data")

        result = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: (
                supabase_client.table("applicants")
                .update({"score_id": str(inserted_id)})
                .eq("id", applicant_id)
                .execute()
            ),
        )

        if not result.data:
            await mongodb.delete_document("scored_candidates", {"_id": inserted_id})
            raise HTTPException(
                status_code=500, detail="Failed to update job applicant"
            )

        return ScoreCandidateResponse(
            message="Candidate scored successfully",
            score_data=raw_output,
        )
    except Exception as e:
        # surface a clear HTTP error
        raise HTTPException(status_code=500, detail=str(e))
