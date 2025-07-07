from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re

from app.dependencies import gemini_model
from app.services.cloudinary_service import fetch_file

router = APIRouter(prefix="/parseresume", tags=["Parse Resume"])

parsing_prompt = "dont give me anything aside from a json file which has the categories: name, city, contact number, email, educational background(with fields:degree,start_date,end_date,institution), soft skills, hard skills, work experience(with fields: title,company,start_date,end_date,description), and projects(with fields:name,start_date,end_date,description). parse this resume:"


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
