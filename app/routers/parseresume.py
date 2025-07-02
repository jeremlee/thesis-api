from fastapi import APIRouter, HTTPException
from typing import Any
import fitz
import os
import json
import re

from app.dependencies import gemini_model, parsing_prompt

router = APIRouter(prefix="/parseresume", tags=["Parse Resume"])


@router.post("/")
def parse_resume(file_path: str) -> dict[str, str] | Any:
    try:
        full_path = os.path.join("resumes", file_path)  # adjust for database later

        if not os.path.exists(full_path):
            return {"error": "File not found."}

        text: str = ""

        with fitz.open(full_path) as doc:
            text = "\n".join(page.get_text() for page in doc)

        response = gemini_model.generate_content(parsing_prompt + "\n" + text)
        raw_output = response.text.strip()

        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        return json.loads(raw_output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model output was not valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
