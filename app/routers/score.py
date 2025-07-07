from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re

from app.dependencies import ScoreInput, gemini_model

router = APIRouter(prefix="/score", tags=["Score"])

scoring_prompt = "score the candidate from 1-10 based on the resume and transcript, dont give me anything but a json with two fields: raw score, and reason"


@router.post("/")
def score_candidate(data: ScoreInput) -> Any:
    try:
        prompt = (
            scoring_prompt
            + "\nResume: "
            + data.resume
            + "\nTranscript: "
            + data.transcript
        )
        response = gemini_model.generate_content(prompt)
        raw_output = response.text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()
        return json.loads(raw_output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model output was not valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
