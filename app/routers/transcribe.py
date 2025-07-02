from fastapi import APIRouter, HTTPException
from typing import Dict, Union, Any
import os

from app.dependencies import gemini_model, transcription_model, sentiment_prompt

router = APIRouter(prefix="/transcribe", tags=["Transcribe"])


@router.post("/")
def transcribe(file_path: str) -> Dict[str, Union[str, Any]]:
    try:
        full_path = os.path.join("interviews", file_path)  # adjust for database later
        if not os.path.exists(full_path):
            return {"error": "File not found."}
        result = transcription_model.transcribe(full_path)
        sentiment_analysis = gemini_model.generate_content(
            f"{sentiment_prompt}{result['text']}"
        )
        return {
            "transcription": result["text"],
            "sentiment_analysis": sentiment_analysis.text.strip(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
