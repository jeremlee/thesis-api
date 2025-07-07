from fastapi import APIRouter, HTTPException
from typing import Dict, Union, Any, List
import os

from app.dependencies import gemini_model, transcription_model

router = APIRouter(prefix="/transcribe", tags=["Transcribe"])

sentiment_prompt = "dont give me anything but a string giving me sentimental analysis and personality traits based on this interview transcript (detailed with at least 100 words). Detailed breakdown of personality traits such as openness, conscientiousness, extroversion, etc.\nTranscript: "


@router.post("/")
def transcribe(file_path: str) -> Dict[str, Union[str, Any]]:
    try:
        full_path = os.path.join("interviews", file_path)  # adjust for database later
        if not os.path.exists(full_path):
            return {"error": "File not found."}
        result: dict[str, str | List[Any]] = transcription_model.transcribe(full_path)
        sentiment_analysis = gemini_model.generate_content(
            f"{sentiment_prompt}{result['text']}"
        )
        return {
            "transcription": result["text"],
            "sentiment_analysis": sentiment_analysis.text.strip(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
