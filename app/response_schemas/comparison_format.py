from pydantic import BaseModel

candidate_comparison_schema = {
    "type": "object",
    "properties": {
        "better_candidate": {
            "type": "string",
            "description": "The name of the candidate who is a better fit for the role based on the comparison.",
        },
        "reason": {
            "type": "string",
            "description": "A clear and concise explanation describing why this candidate is better. Must be between 50 and 100 words.",
        },
        "highlights": {
            "type": "array",
            "description": "An array of short key phrases summarizing the main reasons for choosing this candidate. Each phrase must be no more than 10 words.",
            "items": {"type": "string"},
        },
    },
    "required": [
        "better_candidate",
        "reason",
        "highlights",
    ],
}

class CompareCandidatesResponse(BaseModel):
    better_candidate: str
    reason: str
    highlights: list[str]
