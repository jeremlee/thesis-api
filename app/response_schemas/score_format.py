from pydantic import BaseModel

scoring_response_schema = {
    "type": "object",
    "properties": {
        "reason": {
            "type": "string",
            "description": "A detailed justification for the raw_score, explaining the assessment based on the resume, transcript, and other analyses. Must be at least 100 words.",
        },
        "phrases": {
            "type": "array",
            "description": "An array of key phrases extracted from the reason which give the user an easy-to-read summary by providing phrases about the user, each phrase must be no more than 7 words.",
            "items": {"type": "string"},
        },
        "skill_gaps_recommendations": {
            "type": "string",
            "description": "Highlight any skill gaps in the candidate, along with recommendations for training or development. (at most 50 words only)",
        },
    },
    "required": [
        "reason",
        "phrases",
        "skill_gaps_recommendations",
    ],
}


class ScoreCandidateResponse(BaseModel):
    message: str
    reason: str
    phrases: list[str]
    skill_gaps_recommendations: str
    soft_skills_score: int
    transcription_score: int 
    transcription_cultural_fit_score: int
    cultural_fit_score: int
    response_time: float
    predictive_success: int
    job_fit_score: int
    job_fit_stars: float