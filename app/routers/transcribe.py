from fastapi import APIRouter, HTTPException
from typing import Dict, Union, Any
import os
import json
import re

from app.dependencies import gemini_model, transcription_model, extra_transcript_prompt

router = APIRouter(prefix="/transcribe", tags=["Transcribe"])


@router.post("/")
def transcribe(file_path: str) -> Dict[str, Union[str, Any]]:
    try:
        full_path = os.path.join("interviews", file_path)  # adjust for database later
        if not os.path.exists(full_path):
            return {"error": "File not found."}
        result = transcription_model.transcribe(full_path)
        extra_analysis = gemini_model.generate_content(
            f"{extra_transcript_prompt}{result['text']}"
        )
        gemini_json_string = extra_analysis.text.strip()
        if gemini_json_string.startswith("```json"):
            gemini_json_string = re.sub(r"```json|```", "", gemini_json_string).strip()
        try:
            extra_analysis_data = json.loads(gemini_json_string)
        except json.JSONDecodeError as json_e:
            print(f"Error parsing Gemini's JSON response: {json_e}")
            print(f"Gemini's raw output: {gemini_json_string}")
            raise HTTPException(status_code=500, detail="Failed to parse analysis from AI model.")
        response = {"transcription" : result['text']}
        response.update(extra_analysis_data) #updated with fields (sentimental_analysis, personality_traits, communication_style_insights, interview_insights)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
