from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re
import requests
import PyPDF2
import io

from app.dependencies import parsing_gemini_model, parsing_prompt
from app.services.cloudinary_service import fetch_file, generate_signed_url

router = APIRouter(prefix="/parseresume", tags=["Parse Resume"])


async def extract_text_from_pdf(pdf_url: str) -> str:
    try:
        print(f"Attempting to fetch PDF from URL: {pdf_url}")
        response = requests.get(pdf_url)
        if response.status_code == 401:
            print(f"Unauthorized access. Response: {response.text}")
        response.raise_for_status()

        print(
            f"PDF response status: {response.status_code}, Content-Type: {response.headers.get('content-type')}"
        )
        print(f"PDF content length: {len(response.content)} bytes")

        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        print(f"PDF has {len(pdf_reader.pages)} pages")
        text = ""

        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text() or ""
            print(f"Page {i+1} extracted text length: {len(page_text)}")
            text += page_text + "\n"

        extracted_text = text.strip()
        print(f"Total extracted text length: {len(extracted_text)}")

        if not extracted_text:
            raise Exception(
                "No text could be extracted from the PDF. This might be an image-based PDF."
            )

        return extracted_text
    except Exception as e:
        print(f"Error in extract_text_from_pdf: {str(e)}")
        raise Exception(f"Error extracting text from PDF: {str(e)}")


@router.post("/")
async def parse_resume(public_id: str, applicant_id: str) -> dict[str, str] | Any:
    try:
        file = await fetch_file(public_id)
        print(f"Fetched file metadata: {file}")

        resource_type = file.get("resource_type", "raw")
        pdf_url = generate_signed_url(public_id, resource_type)

        if not pdf_url:
            raise HTTPException(status_code=400, detail="File URL not found")

        print(f"Starting text extraction from: {pdf_url}")
        text: str = await extract_text_from_pdf(pdf_url)
        print(f"Extracted text length: {len(text)} characters")

        if len(text) < 10:  # Very short text might indicate extraction issues
            print("Warning: Very little text extracted from PDF")

        print("Sending text to Gemini model...")
        response = parsing_gemini_model.generate_content(parsing_prompt + "\n" + text)
        raw_output: str = response.text.strip()

        print(f"Raw Gemini output length: {len(raw_output)}")
        print(f"Raw Gemini output preview: {raw_output[:200]}...")

        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        print("Attempting to parse JSON...")
        parsed_result = json.loads(raw_output)
        print("Successfully parsed JSON")
        return parsed_result

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        print(f"Raw output that failed to parse: {raw_output}")
        raise HTTPException(
            status_code=500, detail=f"Model output was not valid JSON: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
