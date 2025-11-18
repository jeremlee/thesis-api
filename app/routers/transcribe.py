import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any, Optional
import json
import re
from transformers import pipeline
import torch

from app.dependencies import (
    transcript_gemini_model,
    transcription_model,
    extra_transcript_prompt,
)
from app.dependencies import localized_transcription_prompt, gemma_path
from app.services.cloudinary_service import fetch_file
from app.services.mongodb_service import mongodb
from app.executor import _executor
from app.services.supabase_service import get_supabase_admin_client

router = APIRouter(prefix="/transcribe", tags=["Transcribe"])

GEMMA_PIPE: Any = None
GEMMA_SEMAPHORE = asyncio.Semaphore()


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

        # localized LLM
        pipe = await get_gemma_pipe()

        text_content = result.get("text", "")

        # Ensure transcription text is a single string (join lists if necessary)
        if isinstance(text_content, list):
            text_content = " ".join([str(t) for t in text_content])

        async with GEMMA_SEMAPHORE:
            raw_output = await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: pipe(
                    localized_transcription_prompt + text_content,
                    max_new_tokens=700,
                    return_full_text=False,
                ),
            )

        # normalize pipeline return value (HF text-generation returns list[dict] with "generated_text")
        if isinstance(raw_output, list):
            out_text = (
                raw_output[0].get("generated_text")
                if isinstance(raw_output[0], dict)
                else str(raw_output[0])
            )
        else:
            out_text = str(raw_output)

        out_text = str(out_text)

        # try to extract JSON from ```json``` fenced block first, fallback to first {...}..{...}
        json_block_pat = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
        json_match = json_block_pat.search(out_text)

        if json_match:
            json_text = json_match.group(1)
        else:
            brace_match = re.search(r"(\{.*\})", out_text, re.S)
            json_text = brace_match.group(1) if brace_match else None

        if json_text:
            try:
                localized_llm_output = json.loads(json_text)
                localized_llm_output.update({"transcription": result.get("text", "")})
            except json.JSONDecodeError:
                # If parsing fails, return raw text so you can inspect it
                localized_llm_output = out_text
        else:
            localized_llm_output = out_text

        await mongodb.delete_document("transcribed", {"user_id": applicant_id})

        inserted_id = await mongodb.insert_document(
            "transcribed",
            {
                "user_id": applicant_id,
                "transcription": localized_llm_output,
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
