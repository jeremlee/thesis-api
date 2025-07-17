from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re

from app.dependencies import gemini_model, parsing_prompt
from app.services.cloudinary_service import fetch_file

router = APIRouter(prefix="/parseresume", tags=["Parse Resume"])



@router.post("/")
async def parse_resume(public_id: str) -> dict[str, str] | Any:
    try:
        file = await fetch_file(public_id)
        print(f"Fetched file metadata: {file}")
        text: str = ""

        response = gemini_model.generate_content(parsing_prompt + "\n" + text)
        raw_output: str = response.text.strip()

        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        return json.loads(raw_output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model output was not valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
