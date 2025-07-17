from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re

from app.dependencies import ScoreInput, scoring_gemini_model, scoring_prompt

router = APIRouter(prefix="/score", tags=["Score"])

@router.post("/")
def score_candidate(data: ScoreInput) -> Any:
    try:
        prompt = (
            scoring_prompt
            + "\n Job: " + data.role
            + "\nResume: "
            + data.resume
            + "\nTranscript: "
            + data.transcript
            + "\n--- Candidate Analysis ---"
            + "\nSentimental Analysis: "
            + data.extra_analysis.sentimental_analysis
            + "\nPersonality Traits: "
            + data.extra_analysis.personality_traits
            + "\nCommunication Style Insights: "
            + data.extra_analysis.communication_style_insights
            + "\nInterview Insights: "
            + data.extra_analysis.interview_insights
        )
        response = scoring_gemini_model.generate_content(prompt)
        raw_output = response.text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()
        return json.loads(raw_output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model output was not valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
