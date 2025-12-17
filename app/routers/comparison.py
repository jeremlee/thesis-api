import asyncio
from typing import Any
import json
from fastapi import HTTPException, Query, APIRouter
from transformers import Pipeline

from app.services.mongodb_service import mongodb
from app.executor import _executor
from app.dependencies import (
    localized_comparison_prompt,
    get_gemma_pipe,
    GEMMA_SEMAPHORE,
    extract_json_text,
)

router = APIRouter(prefix="/compare_candidate", tags=["Compare Candidate"])


def _unwrap_number(val):
    # handle MongoDB serialized numeric types like {"$numberDouble":"1.54"}
    if isinstance(val, dict):
        for k in ("$numberDouble", "$numberInt", "$numberLong"):
            if k in val:
                return val[k]
    return val


def format_score_doc(doc):
    if not doc:
        return "No scoring data found."
    sd = doc.get("score_data", {})
    raw_score = _unwrap_number(sd.get("raw_score")) or sd.get("raw_score")
    predictive = _unwrap_number(sd.get("predictive_success")) or sd.get(
        "predictive_success"
    )
    reason = sd.get("reason", "")
    phrases = sd.get("phrases", [])
    recs = sd.get("skill_gaps_recommendations", "")
    return (
        f"User ID: {doc.get('user_id')}\n"
        f"Job ID: {doc.get('job_id')}\n"
        f"Raw Score: {raw_score}\n"
        f"Predictive Success: {predictive}\n"
        f"Reason: {reason}\n"
        f"Phrases: {', '.join(phrases) if phrases else ''}\n"
        f"Recommendations: {recs}"
    )


@router.get("/")
async def compare_candidates(
    applicant1_id: str = Query(..., description="User ID of the first applicant"),
    applicant2_id: str = Query(..., description="User ID of the second applicant"),
    job_id: str = Query(..., description="Job ID for which applicants are compared"),
) -> Any:
    try:
        (
            score_candidate_A_doc,
            score_candidate_B_doc,
            candidate_A,
            candidate_B,
        ) = await asyncio.gather(
            mongodb.find_document(
                "scored_candidates",
                {"user_id": applicant1_id, "job_id": job_id},
            ),
            mongodb.find_document(
                "scored_candidates",
                {"user_id": applicant2_id, "job_id": job_id},
            ),
            mongodb.find_document(
                "parsed_resume",
                {"user_id": applicant1_id},
            ),
            mongodb.find_document(
                "parsed_resume",
                {"user_id": applicant2_id},
            ),
        )

        if not score_candidate_A_doc or not score_candidate_B_doc:
            raise HTTPException(
                status_code=404,
                detail="Scoring data not found for one or both applicants for the specified job.",
            )

        applicant_A_block = format_score_doc(score_candidate_A_doc)
        applicant_B_block = format_score_doc(score_candidate_B_doc)

        def format_resume_doc(doc):
            if not doc or "raw_output" not in doc:
                return "No resume data found."
            ro = doc["raw_output"]
            return (
                f"Name: {ro.get('name', '')}\n"
                f"City: {ro.get('city', '')}\n"
                f"Contact: {ro.get('contact_number', '')}\n"
                f"Email: {ro.get('email', '')}\n"
                f"Education: {ro.get('educational_background', [])}\n"
                f"Soft Skills: {ro.get('soft_skills', [])}\n"
                f"Hard Skills: {ro.get('hard_skills', [])}\n"
                f"Work Experience: {ro.get('work_experience', [])}\n"
                f"Projects: {ro.get('projects', [])}"
            )

        applicant_A_resume = format_resume_doc(candidate_A)
        applicant_B_resume = format_resume_doc(candidate_B)
        prompt = (
            localized_comparison_prompt
            + "\n\n"
            + "APPLICANT 1 SCORING DATA:\n"
            + applicant_A_block
            + "\n\n"
            + "APPLICANT 1 RESUME DATA:\n"
            + applicant_A_resume
            + "\n\n"
            + "APPLICANT 2 SCORING DATA:\n"
            + applicant_B_block
            + "\n\n"
            + "APPLICANT 2 RESUME DATA:\n"
            + applicant_B_resume
            + "\n\n"
            + "Please compare the two applicants above and provide a concise comparison focused on fit for the job, strengths, weaknesses, and recommended next steps."
        )

        pipe: Pipeline = await get_gemma_pipe()

        async with GEMMA_SEMAPHORE:
            raw_output = await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: pipe(
                    prompt,
                    max_new_tokens=800,
                    return_full_text=False,
                ),
            )

        # normalize pipeline output to a single string (handle list/dict outputs)
        if isinstance(raw_output, str):
            out_text = raw_output
        elif isinstance(raw_output, dict):
            out_text = (
                raw_output.get("generated_text")
                or raw_output.get("text")
                or json.dumps(raw_output)
            )
        elif isinstance(raw_output, list):
            first = raw_output[0] if raw_output else ""
            if isinstance(first, dict):
                out_text = (
                    first.get("generated_text")
                    or first.get("text")
                    or json.dumps(raw_output)
                )
            else:
                out_text = json.dumps(raw_output)
        else:
            out_text = str(raw_output)

        json_text = extract_json_text(out_text)
        if not json_text:
            raise HTTPException(status_code=500, detail="Failed to parse resume JSON")

        return json.loads(json_text)
    except Exception as e:
        pass
