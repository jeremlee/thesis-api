import asyncio
import io
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import PyPDF2
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity
from supabase import Client

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
from app.response_schemas.score_format import ScoreCandidateResponse
from app.response_schemas.transcript_format import TranscriptFormat
from app.services.supabase_service import get_supabase_admin_client
from entities.fastapi.joined import JobListingWithRelations
from entities.fastapi.jsonb import ScoreCandidateFormat
from entities.fastapi.schema_public_latest import (
    PublicApplicants,
    PublicApplicantSkills,
    PublicParsedResume,
    PublicScoredCandidates,
    PublicTranscribed,
)

router = APIRouter(prefix="/score", tags=["Score"])




class JobFitData(BaseModel):
    hard_skills: str
    work_experiences: str
    projects: str


class PredictiveSuccessData(BaseModel):
    soft_skills: str
    transcription: str


class InsertResult(BaseModel):
    inserted_id: str
    applicant_id: str
    raw_output: dict


def _transcribe_video_bytes(video_bytes: bytes, source_name: str) -> dict:
    # Keep original extension when possible so ffmpeg can infer container correctly.
    suffix = Path(source_name).suffix.lower()
    if suffix not in {".mp4", ".webm", ".mov", ".mkv", ".m4a", ".mp3", ".wav"}:
        suffix = ".mp4"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(video_bytes)
            tmp.flush()
            tmp_path = tmp.name

        # If running on CPU-only, fp16=False avoids warnings/errors on some setups.
        return transcription_model.transcribe(tmp_path, fp16=False)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


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


async def extract_text_from_pdf_url(pdf_bytes: bytes) -> str:
    def _extract_text() -> str:
        text: str = ""
        for page in PyPDF2.PdfReader(io.BytesIO(pdf_bytes)).pages:
            text += (page.extract_text() or "") + "\n"
        output = text.strip()
        if not output:
            raise ValueError("No text could be extracted from the PDF.")
        return output

    return await asyncio.to_thread(_extract_text)


async def ensure_parsed_resume(
    applicant_id: str, resume_path: str, supabase_client: Client, resume_id: UUID | None
) -> InsertResult:
    """
    Ensures that the resume is parsed and stored in the database.
    If a parsed resume already exists for the applicant,
    it will be deleted and re-parsed to ensure the latest version is used.

    Args:
        applicant_id (str): The ID of the applicant.
        resume_path (str): The path to the resume file in Supabase storage.
        supabase_client (Client): The Supabase client instance.
        resume_id (str): The ID of the existing parsed resume to delete.
    Returns:
        InsertResult: A dictionary containing the parsed resume data and related information.
    """

    bucket, file_name = resume_path.split("/", 1)

    download_result, _ = await asyncio.gather(
        asyncio.to_thread(
            lambda: supabase_client.storage.from_(bucket).download(file_name)
        ),
        (
            asyncio.to_thread(
                lambda: (
                    supabase_client.table("parsed_resume")
                    .delete()
                    .eq("id", resume_id)
                    .execute()
                )
            )
            if resume_id
            else asyncio.to_thread(lambda: None)
        ),
    )

    if not download_result:
        raise HTTPException(status_code=404, detail="Downloaded resume is empty")

    text: str = await extract_text_from_pdf_url(download_result)

    parsed_output = extract_json_payload(
        await asyncio.to_thread(
            lambda: parsing_gemini_model.generate_content(
                parsing_prompt + "\n" + text
            ).text.strip(),
        )
    )

    inserted_row = await asyncio.to_thread(
        lambda: (
            supabase_client.table("parsed_resume")
            .insert({"parsed_resume": parsed_output})
            .execute()
            .data
        ),
    )

    if not inserted_row:
        raise HTTPException(status_code=500, detail="Insert returned no data")

    inserted_row = inserted_row[0]
    if inserted_row is None or not isinstance(inserted_row, dict):
        raise HTTPException(status_code=500, detail="Inserted row is invalid or None")

    inserted_row["parsed_resume"] = json.dumps(inserted_row.get("parsed_resume"))

    inserted: PublicParsedResume = PublicParsedResume.model_validate(inserted_row)

    await asyncio.to_thread(
        lambda: (
            supabase_client.table("applicants")
            .update({"parsed_resume_id": str(inserted.id)})
            .eq("id", applicant_id)
            .execute()
        ),
    )

    return InsertResult(
        inserted_id=str(inserted.id),
        applicant_id=applicant_id,
        raw_output=parsed_output,
    )


async def ensure_transcription(
    applicant_id: str, video_path: str, supabase_client, transcript_id: UUID | None
) -> InsertResult:

    bucket, file_name = video_path.split("/", 1)

    download_result, _ = await asyncio.gather(
        asyncio.to_thread(
            lambda: supabase_client.storage.from_(bucket).download(file_name)
        ),
        (
            asyncio.to_thread(
                lambda: (
                    supabase_client.table("transcribed")
                    .delete()
                    .eq("id", transcript_id)
                    .execute()
                )
            )
            if transcript_id
            else asyncio.sleep(0)
        ),
    )

    if not download_result:
        raise HTTPException(status_code=400, detail="Downloaded video is empty")

    transcript_result = await asyncio.to_thread(
        lambda: _transcribe_video_bytes(download_result, video_path)
    )

    extra_analysis_data: TranscriptFormat = TranscriptFormat.model_validate(
        extract_json_payload(
            await asyncio.to_thread(
                lambda: transcript_gemini_model.generate_content(
                    f"{extra_transcript_prompt}{transcript_result['text']}"
                ).text.strip(),
            )
        )
    )

    payload: dict[Any, Any] = {"transcription": transcript_result["text"]}
    payload.update(extra_analysis_data.model_dump())

    inserted_row = await asyncio.to_thread(
        lambda: (
            supabase_client.table("transcribed")
            .insert({"transcription": payload})
            .execute()
            .data
        ),
    )

    if not inserted_row:
        raise HTTPException(
            status_code=500, detail="Failed to insert transcription data"
        )

    inserted_row = inserted_row[0]
    if inserted_row is None or not isinstance(inserted_row, dict):
        raise HTTPException(status_code=500, detail="Inserted row is invalid or None")

    inserted_row["transcription"] = json.dumps(inserted_row.get("transcription", {}))

    inserted: PublicTranscribed = PublicTranscribed.model_validate(inserted_row)

    await asyncio.to_thread(
        lambda: (
            supabase_client.table("applicants")
            .update({"transcribed_id": str(inserted.id)})
            .eq("id", applicant_id)
            .execute()
        ),
    )

    return InsertResult(
        inserted_id=str(inserted.id),
        applicant_id=applicant_id,
        raw_output=payload,
    )


@router.post("/")
async def score_candidate(
    applicant_id: str = Query(..., description="Applicant ID"),
    benchmark: float = Query(..., description="Benchmark value (harshness of scoring)"),
    soft_skills_weight: float = Query(..., description="Soft skills score weight"),
    transcription_weight: float = Query(..., description="Transcription score weight"),
    cultural_fit_weight: float = Query(..., description="Cultural fit score weight"),
    transcription_cultural_weight: float = Query(..., description="Transcription cultural fit score weight"),
    job_fit_weight: float = Query(..., description="Job fit score weight"),
    behavioral_blend_weight: float = Query(..., description="Behavioral blend score weight"),
) -> ScoreCandidateResponse:
    
    # validating
    if benchmark <= 0.0 or benchmark >= 1.0:
        raise HTTPException(
            status_code=400,
            detail="Benchmark must be greater than 0.0 and less than 1.0 (0.65-0.85 is recommended)",
        )
    # checking if everything adds up to 1.0
    if not abs(
        soft_skills_weight
        + transcription_weight
        + cultural_fit_weight
        + transcription_cultural_weight
        - 1.0
    ) < 1e-6:
        raise HTTPException(
            status_code=400,
            detail="Behavioral weights must sum to 1.0",
        )

    if not abs(job_fit_weight + behavioral_blend_weight - 1.0) < 1e-6:
        raise HTTPException(
            status_code=400,
            detail="Final weights must sum to 1.0",
        )

    supabase_client: Client = get_supabase_admin_client()

    applicant_data: PublicApplicants = PublicApplicants.model_validate(
        await asyncio.to_thread(
            lambda: (
                supabase_client.table("applicants")
                .select("*")
                .eq("id", applicant_id)
                .single()
                .execute()
                .data
            ),
        )
    )

    if applicant_data.score_id:
        await asyncio.to_thread(
            lambda: (
                supabase_client.table("scored_candidates")
                .delete()
                .eq("id", applicant_data.score_id)
                .execute()
            )
        )

    try:
        parsed_resume, transcribed, job_listing_data = await asyncio.gather(
            ensure_parsed_resume(
                applicant_id,
                applicant_data.resume_id,
                supabase_client,
                applicant_data.parsed_resume_id,
            ),
            ensure_transcription(
                applicant_id,
                applicant_data.transcript_id,
                supabase_client,
                applicant_data.transcribed_id,
            ),
            asyncio.to_thread(
                lambda: (
                    supabase_client.table("job_listings")
                    .select("*, jl_requirements(*), job_tags(*, tags(*))")
                    .eq("id", applicant_data.joblisting_id)
                    .single()
                    .execute()
                    .data
                ),
            ),
        )

        job_listing_data = JobListingWithRelations.model_validate(job_listing_data)

        if not transcribed:
            transcribed = InsertResult(
                inserted_id="",
                applicant_id=applicant_id,
                raw_output={
                    "transcription": "No transcription available",
                    "sentimental_analysis": "No sentimental analysis found",
                    "personality_traits": "No personality traits found",
                    "communication_style_insights": "No communication style insights found",
                    "interview_insights": "No interview insights found",
                },
            )

        applicant_skills: list[PublicApplicantSkills] = [
            PublicApplicantSkills.model_validate(applicant_skill)
            for applicant_skill in await asyncio.to_thread(
                lambda: (
                    supabase_client.table("applicant_skills")
                    .select("*")
                    .eq("applicant_id", applicant_id)
                    .execute()
                    .data
                ),
            )
        ]

        skills_lookup: dict[int, int] = {s.tag_id: s.rating for s in applicant_skills}

        tag_list: list[str] = [t.tags.name for t in job_listing_data.job_tags]

        resume_json = parsed_resume.raw_output
        job_fit_data: JobFitData = get_job_fit_data(resume_json)
        predictive_success_data: PredictiveSuccessData = get_predictive_success_data(
            resume_json,
            transcribed.raw_output["transcription"],
        )

        # converts hard skills, work experiences, projects to numerical vector
        job_fit_embedding = embedding_model.encode(
            (
                f"TECHNICAL SKILLS:\n{job_fit_data.hard_skills}\n\n"
                f"PROFESSIONAL EXPERIENCE:\n{job_fit_data.work_experiences}\n\n"
                f"TECHNICAL PROJECTS:\n{job_fit_data.projects}"
            ),
            normalize_embeddings=True,
        )

        # converts soft skills to numerical vector
        soft_skills_embedding: np.ndarray = embedding_model.encode(
            f"SOFT SKILLS:\n{predictive_success_data.soft_skills}\n\n",
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        # converts transcription to numerical vector
        transcription_emb: np.ndarray = embedding_model.encode(
            (f"TRANSCRIPTION:\n{predictive_success_data.transcription}\n\n"),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        # converts job requirements text and tags to numerical vector
        job_emb: np.ndarray = embedding_model.encode(
            "Requirements: "
            + "; ".join(r.requirement for r in job_listing_data.jl_requirements)
            + "\n"
            + "Tags: "
            + ", ".join(tag_list),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        # converts the company's core values to numerical vector
        cultural_fit_emb: np.ndarray = embedding_model.encode(
            core_values, normalize_embeddings=True, convert_to_numpy=True
        )

        # converts the soft skills baseline (the ideal standard for soft skills) to numerical vector
        soft_skills_baseline_emb: np.ndarray = embedding_model.encode(
            soft_skills_baseline, normalize_embeddings=True, convert_to_numpy=True
        )
        # THE NUMERICAL VECTORS WILL BE USED TO COMPUTE THE SCORES THROUGH COSINE SIMILARITY
        # computes the cosine similarity between the job_fit_data (hard skills, work experiences and projects) and the job requirements
        # take note that job_fit_score was previously referred to as raw_score

        job_fit_score = float(
            cosine_similarity(
                np.asarray(job_fit_embedding).reshape(1, -1),
                np.asarray(job_emb).reshape(1, -1),
            )[0][0]
        )

        # computes the cosine similarity between the soft skills and the soft skills standard

        soft_skills_score = float(
            cosine_similarity(
                np.asarray(soft_skills_embedding).reshape(1, -1),
                np.asarray(soft_skills_baseline_emb).reshape(1, -1),
            )[0][0]
        )

        # computes the cosine similarity between the transcription data and the soft skills standard

        transcription_score = float(
            cosine_similarity(
                np.asarray(transcription_emb).reshape(1, -1),
                np.asarray(soft_skills_baseline_emb).reshape(1, -1),
            )[0][0]
        )

        # computes the cosine similarity between the soft skills and the cultural fit

        cultural_fit_score = float(
            cosine_similarity(
                np.asarray(soft_skills_embedding).reshape(1, -1),
                np.asarray(cultural_fit_emb).reshape(1, -1),
            )[0][0]
        )

        # computes the cosine similarity between the transcription data and the cultural fit

        transcription_cultural_fit_score = float(
            cosine_similarity(
                np.asarray(transcription_emb).reshape(1, -1),
                np.asarray(cultural_fit_emb).reshape(1, -1),
            )[0][0]
        )

        # 1. Calculate the Behavioral Blend (The "How they work" side)

        behavioral_blend = (
            (transcription_cultural_fit_score * transcription_cultural_weight)
            + (transcription_score * transcription_weight)
            + (cultural_fit_score * cultural_fit_weight)
            + (soft_skills_score * soft_skills_weight)
        )

        # normalizing values

        soft_skills_score_pct = min(100, int((soft_skills_score / benchmark) * 100))
        transcription_score_pct = min(100, int((transcription_score / benchmark) * 100))
        cultural_fit_score_pct = min(100, int((cultural_fit_score / benchmark) * 100))
        trans_cultural_fit_score_pct = min(
            100, int((transcription_cultural_fit_score / benchmark) * 100)
        )

        # 2. Calculate Final Predictive Success (with the according weights)

        # This results in a value between 0.0 and 1.0

        predictive_success_raw: float = (job_fit_score * job_fit_weight) + (behavioral_blend * behavioral_blend_weight)

        # 3. Scaling for Human Readability

        # Since MPNet scores rarely hit 1.0, we scale the result.

        predictive_success_final_score: int = min(
            100, int((predictive_success_raw / benchmark) * 100)
        )

        # 4. Job Fit Score (1-5 Star Rating)

        # Similarly, we scale 0.85 similarity to be a 5-star result. 0.85 is the perfect score (replaced with benchmark input)
        job_fit_final_score: int = min(100, int((job_fit_score / benchmark) * 100))
        job_fit_stars = float(round(min(5.0, (job_fit_score / benchmark) * 5), 1))

        """
        scores are based from:
        job fit score (previously raw_score) = hard skills from resume, work experiences, projects
        predictive success = soft skills from resume, transcription, cultural fit
        """

        # PROMPT SECTION
        prompt = (
            localized_scoring_prompt
            + "\n Job: "
            + job_listing_data.title
            + "\nResume: "
            + json.dumps(parsed_resume.raw_output, ensure_ascii=False)
            + "\nJob Tags: "
            + ", ".join(name for name in tag_list)
            + "\nTranscript: "
            + transcribed.raw_output.get("transcription", "No transcription data found")
            + "\n--- Candidate Analysis ---"
            + "\nSentimental Analysis: "
            + transcribed.raw_output.get(
                "sentimental_analysis", "No sentimental analysis found"
            )
            + "\nPersonality Traits: "
            + transcribed.raw_output.get(
                "personality_traits", "No personality traits found"
            )
            + "\nCommunication Style Insights: "
            + transcribed.raw_output.get(
                "communication_style_insights",
                "No communication style insights found",
            )
            + "\nInterview Insights: "
            + transcribed.raw_output.get(
                "interview_insights", "No interview insights found"
            )
            + "Applicant skillS (self-rating): "
            + "\n".join(
                f"{job_listing_tag.tags.name} : {skills_lookup[job_listing_tag.tags.id]}"
                for job_listing_tag in job_listing_data.job_tags
                if job_listing_tag.tags.id in skills_lookup
            )
            + "CALCULATED SCORES BY COSINE SIMILARITY: \n"
            + f"JOB_FIT_SCORE = {job_fit_final_score}\n"
            + f"PREDICTIVE_SUCCESS_SCORE = {predictive_success_final_score}"
        )

        start_time = time.perf_counter()
        raw_output = await asyncio.to_thread(
            lambda: scoring_gemini_model.generate_content(prompt).text.strip(),
        )
        end_time = time.perf_counter()
        duration = end_time - start_time  # Seconds
        response_time = round(duration, 2)
        validated_score: ScoreCandidateFormat = ScoreCandidateFormat.model_validate(
            extract_json_payload(raw_output)
        )

        raw_output = (
            validated_score.model_dump()
        )  # Convert to dict for storage and response

        # use these for success likelihood "visualization"
        raw_output["soft_skills_score"] = soft_skills_score_pct
        raw_output["transcription_score"] = transcription_score_pct
        raw_output["transcription_cultural_fit_score"] = trans_cultural_fit_score_pct
        raw_output["cultural_fit_score"] = cultural_fit_score_pct

        # response time
        raw_output["response_time"] = response_time

        # adding the scores to the field
        # final scores
        raw_output["predictive_success"] = predictive_success_final_score
        raw_output["job_fit_score"] = job_fit_final_score
        raw_output["job_fit_stars"] = job_fit_stars

        # dynamic weights added to the json raw_output
        raw_output["soft_skills_weight"] = soft_skills_weight
        raw_output["benchmark"] = benchmark
        raw_output["transcription_weight"] = transcription_weight
        raw_output["cultural_fit_weight"] = cultural_fit_weight
        raw_output["transcription_cultural_weight"] = transcription_cultural_weight
        raw_output["job_fit_weight"] = job_fit_weight
        raw_output["behavioral_blend_weight"] = behavioral_blend_weight
        # Ensure BSON-safe payload (ObjectId/numpy scalars/nested structures)
        raw_output = _convert_value(raw_output)

        # Ensure raw_output is a dict before passing to convert_objectid
        if not isinstance(raw_output, dict):
            raise HTTPException(status_code=500, detail="Invalid score data format")

        inserted_row = await asyncio.to_thread(
            lambda: (
                supabase_client.table("scored_candidates")
                .insert(
                    {
                        "score_data": raw_output,
                    },
                )
                .execute()
                .data
            ),
        )

        if not inserted_row:
            raise HTTPException(
                status_code=500, detail="Failed to insert scored candidate data"
            )

        inserted_row = inserted_row[0]
        if inserted_row is None or not isinstance(inserted_row, dict):
            raise HTTPException(
                status_code=500,
                detail="Inserted scored candidate row is invalid or None",
            )

        inserted_row["score_data"] = json.dumps(inserted_row.get("score_data", {}))

        inserted_scored_candidates: PublicScoredCandidates = (
            PublicScoredCandidates.model_validate(inserted_row)
        )

        result = await asyncio.to_thread(
            lambda: (
                supabase_client.table("applicants")
                .update({"score_id": str(inserted_scored_candidates.id)})
                .eq("id", applicant_id)
                .execute()
            ),
        )

        if not result.data:
            await asyncio.to_thread(
                lambda: (
                    supabase_client.table("scored_candidates")
                    .delete()
                    .eq("id", inserted_scored_candidates.id)
                    .execute()
                ),
            )
            raise HTTPException(
                status_code=500, detail="Failed to update job applicant"
            )

        return ScoreCandidateResponse(
            message="Candidate scored successfully",
            reason=validated_score.reason,
            phrases=validated_score.phrases,
            skill_gaps_recommendations=validated_score.skill_gaps_recommendations,
            soft_skills_score=soft_skills_score_pct,
            transcription_score=transcription_score_pct,
            transcription_cultural_fit_score=trans_cultural_fit_score_pct,
            cultural_fit_score=cultural_fit_score_pct,
            response_time=response_time,
            predictive_success=predictive_success_final_score,
            job_fit_score=job_fit_final_score,
            job_fit_stars=job_fit_stars,
        )
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
