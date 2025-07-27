import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re
import requests
import PyPDF2
import io

from app.dependencies import parsing_gemini_model, parsing_prompt
from app.services.cloudinary_service import fetch_file, generate_signed_url
from app.executor import _executor
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

        raw_output = await asyncio.get_event_loop().run_in_executor(
            _executor,
            lambda: parsing_gemini_model.generate_content(
                parsing_prompt + "\n" + text
            ).text.strip(),
        )

        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        await mongodb.delete_document(
            "parsed_resume",
            {"applicant_id": applicant_id},
        )

        inserted_id = await mongodb.insert_document(
            "parsed_resume",
            {
                "user_id": applicant_id,
                "raw_output": json.loads(raw_output),
            },
        )

        if not inserted_id:
            raise HTTPException(
                status_code=500, detail="Failed to insert parsed resume"
            )

        result = await asyncio.get_event_loop().run_in_executor(
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
