import asyncio
import json
import re
from fastapi import APIRouter, HTTPException, Query
from typing import Any

from app.services.mongodb_service import mongodb
from app.services.supabase_service import get_supabase_admin_client
from app.executor import _executor
from app.dependencies import localized_scoring_prompt, scoring_gemini_model


router = APIRouter(prefix="/score", tags=["Score"])


# Convert ObjectId to string for JSON serialization from MongoDB
def convert_objectid(obj):
    from bson import ObjectId

    match obj:
        case None:
            return None
        case ObjectId():
            return str(obj)
        case dict():
            return {k: convert_objectid(v) for k, v in obj.items()}
        case list():
            return [convert_objectid(item) for item in obj]

    return obj


@router.post("/")
async def score_candidate(
    user_id: str = Query(..., description="User ID"),
    job_id: str = Query(..., description="Job ID"),
    applicant_id: str = Query(..., description="Applicant ID"),
) -> Any:
    supabase_client = get_supabase_admin_client()
    try:
        job_listing_data, transcribed, parsed_resume = await asyncio.gather(
            asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: supabase_client.table("job_listings")
                .select("title")
                .eq("id", job_id)
                .single()
                .execute(),
            ),
            mongodb.find_document(
                "transcribed",
                {"user_id": user_id},
            ),
            mongodb.find_document(
                "parsed_resume",
                {"user_id": user_id},
            ),
        )

        if not job_listing_data:
            raise HTTPException(status_code=404, detail="Job listing not found")

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

        tags = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("job_tags")
            .select("*, tags(*)")
            .eq("joblisting_id", job_id)
            .execute(),
        )

        tags = [
            str(tag["tags"]["name"])
            for tag in tags.data
            if "tags" in tag and "name" in tag["tags"]
        ]

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
        )

        raw_output = scoring_gemini_model.generate_content(prompt).text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        raw_output = json.loads(raw_output)

        inserted_id = await mongodb.insert_document(
            "scored_candidates",
            {
                "user_id": user_id,
                "job_id": job_id,
                "score_data": raw_output,
            },
        )

        if not inserted_id:
            await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: supabase_client.table("job_applicants")
                .delete()
                .eq("id", applicant_id)
                .execute(),
            )
            raise HTTPException(status_code=500, detail="Failed to insert score data")

        result = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: supabase_client.table("job_applicants")
            .update({"score_id": str(inserted_id)})
            .eq("id", applicant_id)
            .execute(),
        )

        if not result.data:
            await mongodb.delete_document("scored_candidates", {"_id": inserted_id})
            raise HTTPException(
                status_code=500, detail="Failed to update job applicant"
            )

        return {
            "message": "Candidate scored successfully",
            "score_data": convert_objectid(raw_output),
        }
    except Exception as e:
        await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: supabase_client.table("job_applicants")
            .delete()
            .eq("id", applicant_id)
            .execute(),
        )

        # surface a clear HTTP error
        raise HTTPException(status_code=500, detail=str(e))
