import asyncio
import json
from typing import TypeVar, Type, Optional
from fastapi import HTTPException, Query, APIRouter
import re
from supabase import Client
from pydantic import BaseModel

from app.dependencies import localized_comparison_prompt, comparing_gemini_model
from app.response_schemas.comparison_format import CompareCandidatesResponse
from app.services.supabase_service import get_supabase_admin_client
from entities.fastapi.jsonb import ParsedResumeData, ScoredCandidateData
from entities.fastapi.schema_public_latest import (
    PublicApplicants,
)

router = APIRouter(prefix="/compare_candidate", tags=["Compare Candidate"])


def _find_pydantic(rows, id_):
    return next((r for r in (rows or []) if str(r.id) == str(id_)), None)


def _find_dict(rows, id_):
    return next((r for r in (rows or []) if str(r.get("id")) == str(id_)), None)


T = TypeVar("T", bound=BaseModel)


def _extract_and_validate(row, label, field_name, model_cls: Type[T]) -> T:
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"{label} not found for the specified job.",
        )
    if not isinstance(row, dict):
        raise HTTPException(
            status_code=500,
            detail=f"Invalid {label}: {row}",
        )
    try:
        return model_cls.model_validate(row.get(field_name, {}))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _unwrap_number(val):
    # handle MongoDB serialized numeric types like {"$numberDouble":"1.54"}
    if isinstance(val, dict):
        for k in ("$numberDouble", "$numberInt", "$numberLong"):
            if k in val:
                return val[k]
    return val


def format_score_doc(doc: Optional[ScoredCandidateData]) -> str:
    # raw_score = _unwrap_number(sd.) or sd.raw_score
    # predictive = _unwrap_number(sd.get("predictive_success")) or sd.get(
    #     "predictive_success"
    # )
    # reason = sd.get("reason", "")
    # phrases = sd.get("phrases", [])
    # recs = sd.get("skill_gaps_recommendations", "")
    # return (
    #     f"User ID: {doc.get('user_id')}\n"
    #     f"Job ID: {doc.get('job_id')}\n"
    #     f"Raw Score: {raw_score}\n"
    #     f"Predictive Success: {predictive}\n"
    #     f"Reason: {reason}\n"
    #     f"Phrases: {', '.join(phrases) if phrases else ''}\n"
    #     f"Recommendations: {recs}"
    # )
    return ""


def format_resume_doc(doc: Optional[ParsedResumeData]) -> str:
    if doc is None:
        return "No resume data available."

    return (
        f"Name: {doc.name}\n"
        f"Education: {doc.educational_background}\n"
        f"Soft Skills: {doc.soft_skills}\n"
        f"Hard Skills: {doc.hard_skills}\n"
        f"Work Experience: {doc.work_experience}\n"
        f"Projects: {doc.projects}"
    )


@router.get("/")
async def compare_candidates(
    applicant1_id: str = Query(..., description="User ID of the first applicant"),
    applicant2_id: str = Query(..., description="User ID of the second applicant"),
) -> CompareCandidatesResponse:
    try:
        supabase_client: Client = get_supabase_admin_client()

        candidates: list[PublicApplicants] = [
            PublicApplicants.model_validate(applicant)
            for applicant in await asyncio.to_thread(
                lambda: (
                    supabase_client.table("applicants")
                    .select("*")
                    .in_("id", [applicant1_id, applicant2_id])
                    .execute()
                    .data
                ),
            )
        ]

        candidate_A = _find_pydantic(candidates, applicant1_id)
        candidate_B = _find_pydantic(candidates, applicant2_id)

        if not candidate_A or not candidate_B:
            raise HTTPException(
                status_code=404,
                detail="One or both applicants not found in the database.",
            )

        scored_rows, parsed_rows = await asyncio.gather(
            asyncio.to_thread(
                lambda: (
                    supabase_client.table("scored_candidates")
                    .select("*")
                    .in_("id", [str(candidate_A.score_id), str(candidate_B.score_id)])
                    .execute()
                    .data
                )
            ),
            asyncio.to_thread(
                lambda: (
                    supabase_client.table("parsed_resume")
                    .select("*")
                    .in_(
                        "id",
                        [
                            str(candidate_A.parsed_resume_id),
                            str(candidate_B.parsed_resume_id),
                        ],
                    )
                    .execute()
                    .data
                )
            ),
        )

        [score_candidate_A, score_candidate_B] = [
            _extract_and_validate(
                _find_dict(scored_rows, candidate_A.score_id),
                "scoring data for applicant 1",
                "score_data",
                ScoredCandidateData,
            ),
            _extract_and_validate(
                _find_dict(scored_rows, candidate_B.score_id),
                "scoring data for applicant 2",
                "score_data",
                ScoredCandidateData,
            ),
        ]

        [resume_candidate_A, resume_candidate_B] = [
            _extract_and_validate(
                _find_dict(parsed_rows, candidate_A.parsed_resume_id),
                "resume data for applicant 1",
                "parsed_resume",
                ParsedResumeData,
            ),
            _extract_and_validate(
                _find_dict(parsed_rows, candidate_B.parsed_resume_id),
                "resume data for applicant 2",
                "parsed_resume",
                ParsedResumeData,
            ),
        ]

        prompt: str = (
            localized_comparison_prompt
            + "\n\n"
            + "APPLICANT 1 SCORING DATA:\n"
            + format_score_doc(score_candidate_A)
            + "\n\n"
            + "APPLICANT 1 RESUME DATA:\n"
            + format_resume_doc(resume_candidate_A)
            + "\n\n"
            + "APPLICANT 2 SCORING DATA:\n"
            + format_score_doc(score_candidate_B)
            + "\n\n"
            + "APPLICANT 2 RESUME DATA:\n"
            + format_resume_doc(resume_candidate_B)
            + "\n\n"
            + "Please compare the two applicants above and provide a concise comparison focused on fit for the job, strengths, weaknesses, and recommended next steps."
        )

        raw_output: str = comparing_gemini_model.generate_content(prompt).text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        comparison_dict = json.loads(raw_output)
        return CompareCandidatesResponse(**comparison_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
