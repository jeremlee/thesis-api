import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re
import requests
import PyPDF2
import io
from transformers import Pipeline
import PyPDF2
from json import JSONDecoder, JSONDecodeError

from app.dependencies import localized_parsing_prompt, get_gemma_pipe, GEMMA_SEMAPHORE
from app.executor import _executor
from app.services.cloudinary_service import fetch_file, generate_signed_url
from app.services.mongodb_service import mongodb
from app.services.supabase_service import get_supabase_admin_client

router = APIRouter(prefix="/parseresume", tags=["Parse Resume"])


async def extract_text_from_pdf(pdf_url: str) -> str:
    def _extract_text():
        try:
            text = ""

            for page in PyPDF2.PdfReader(
                io.BytesIO(requests.get(pdf_url).content)
            ).pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"

            extracted_text = text.strip()

            if not extracted_text:
                raise Exception(
                    "No text could be extracted from the PDF. This might be an image-based PDF."
                )

            return extracted_text
        except Exception as e:
            print(f"Error in extract_text_from_pdf: {str(e)}")
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    return await asyncio.get_running_loop().run_in_executor(_executor, _extract_text)


@router.post("/")
async def parse_resume(public_id: str, applicant_id: str) -> dict[str, str] | Any:
    try:
        file = await fetch_file(public_id)

        resource_type = file.get("resource_type", "raw")  # type: ignore
        pdf_url = generate_signed_url(public_id, resource_type)

        if not pdf_url:
            raise HTTPException(status_code=400, detail="File URL not found")

        text: str = await extract_text_from_pdf(pdf_url)
        pipe: Pipeline = await get_gemma_pipe()

        async with GEMMA_SEMAPHORE:
            raw_output = await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: pipe(
                    localized_parsing_prompt + text,
                    max_new_tokens=3000,
                    return_full_text=False,
                ),
            )

        print(f"Raw output from pipeline: {raw_output}")

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

        print(f"Raw LLM Output: {out_text}")

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
                    obj, idx = decoder.raw_decode(s[start:])
                    return s[start : start + idx]
                except JSONDecodeError:
                    start = s.find("{", start + 1)
            return None

        json_text = extract_json_text(out_text)
        if not json_text:
            raise HTTPException(status_code=500, detail="Failed to parse resume JSON")

        try:
            localized_llm_output = json.loads(json_text)["parsed_resume"]
        except JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON from LLM: {e}")

        await mongodb.delete_document(
            "parsed_resume",
            {"applicant_id": applicant_id},
        )

        inserted_id = await mongodb.insert_document(
            "parsed_resume",
            {
                "user_id": applicant_id,
                "raw_output": localized_llm_output,
            },
        )

        if not inserted_id:
            raise HTTPException(
                status_code=500, detail="Failed to insert parsed resume"
            )

        result = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("users")
            .update({"parsed_resume_id": str(inserted_id)})
            .eq("id", applicant_id)
            .execute(),
        )

        if not result.data:
            await mongodb.delete_document("parsed_resume", {"_id": inserted_id})
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "message": "Resume parsed successfully",
            "parsed_resume_id": str(inserted_id),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/")
async def delete_parsed_resume(applicant_id: str):
    await asyncio.gather(
        mongodb.delete_document("parsed_resume", {"user_id": applicant_id}),
        asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("users")
            .update({"parsed_resume_id": None})
            .eq("id", applicant_id)
            .execute(),
        ),
    )
