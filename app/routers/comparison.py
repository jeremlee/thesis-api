import asyncio
from fastapi import APIRouter
from typing import Any
import json
from json import JSONDecoder, JSONDecodeError
from fastapi import HTTPException
import re

from app.services.mongodb_service import mongodb
from app.executor import _executor
from app.dependencies import (
    localized_comparison_prompt,
    get_gemma_pipe,
    GEMMA_SEMAPHORE,
)
from transformers import Pipeline

router = APIRouter(prefix="/compare_candidate", tags=["Compare Candidate"])


@router.get("/")
async def compare_candidates(
    applicant1_id: str, applicant2_id: str, job_id: str
) -> Any:
    try:
        score_candidate_A_doc, score_candidate_B_doc = await asyncio.gather(
            mongodb.find_document(
                "scored_candidates",
                {"user_id": applicant1_id, "job_id": job_id},
            ),
            mongodb.find_document(
                "scored_candidates",
                {"user_id": applicant2_id, "job_id": job_id},
            ),
        )

        def _unwrap_number(val):
            # handle MongoDB serialised numeric types like {"$numberDouble":"1.54"}
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

        applicant_A_block = format_score_doc(score_candidate_A_doc)
        applicant_B_block = format_score_doc(score_candidate_B_doc)

        prompt = (
            localized_comparison_prompt
            + "\n\n"
            + "APPLICANT 1 SCORING DATA:\n"
            + applicant_A_block
            + "\n\n"
            + "APPLICANT 2 SCORING DATA:\n"
            + applicant_B_block
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

        json_text = extract_json_text(out_text)
        if not json_text:
            raise HTTPException(status_code=500, detail="Failed to parse resume JSON")

        return json.loads(json_text)
    except Exception as e:
        pass
