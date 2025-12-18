import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re

from app.dependencies import (
    transcription_model,
    transcript_gemini_model,
    extra_transcript_prompt,
)
from app.services.cloudinary_service import fetch_file
from app.services.mongodb_service import mongodb
from app.executor import _executor
from app.services.supabase_service import get_supabase_admin_client


router = APIRouter(prefix="/transcribe", tags=["Transcribe"])


@router.post("/")
async def transcribe(public_id: str, applicant_id: str) -> dict[str, str] | Any:
    try:
        video_metadata = await fetch_file(public_id, resource_type="video")
        if not video_metadata:
            raise HTTPException(status_code=400, detail="File URL not found")

        video_url = video_metadata.get("secure_url") or video_metadata.get("url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Video URL not found")

        result = transcription_model.transcribe(video_url)

        extra_analysis = transcript_gemini_model.generate_content(
            f"{extra_transcript_prompt}{result['text']}"
        )
        gemini_json_string = extra_analysis.text.strip()

        if gemini_json_string.startswith("```json"):
            gemini_json_string = re.sub(r"```json|```", "", gemini_json_string).strip()
        try:
            extra_analysis_data = json.loads(gemini_json_string)
        except json.JSONDecodeError as json_e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse analysis from AI model. Error: {str(json_e)}",
            )

        result = {"transcription": result["text"]}
        result.update(extra_analysis_data)

        await mongodb.delete_document("transcribed", {"user_id": applicant_id})

        inserted_id = await mongodb.insert_document(
            "transcribed",
            {
                "user_id": applicant_id,
                "transcription": result,
            },
        )

        if not inserted_id:
            raise HTTPException(
                status_code=500, detail="Failed to insert transcription"
            )

        result = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("users")
            .update({"transcribed_id": str(inserted_id)})
            .eq("id", applicant_id)
            .execute(),
        )

        if not result.data:
            await mongodb.delete_document("transcribed", {"_id": inserted_id})
            raise HTTPException(
                status_code=500, detail="Failed to update user with transcription ID"
            )

        return {
            "message": "Transcription completed successfully",
            "transcribed_id": str(inserted_id),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/")
async def delete_transcription(applicant_id: str):
    await asyncio.gather(
        mongodb.delete_document("transcribed", {"user_id": applicant_id}),
        asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("users")
            .update({"transcribed_id": None})
            .eq("id", applicant_id)
            .execute(),
        ),
    )

    return {"message": "Transcription deleted successfully"}
