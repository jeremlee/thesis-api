scoring_response_schema = {
    "type": "object",
    "properties": {
        "raw_score": {
            "type": "number", 
            "description": "The candidate's score indicating their fitness for the role, on a scale of 1.00 to 5.00, with exactly two decimal places."
        },
        "reason": {
            "type": "string",
            "description": "A detailed justification for the raw_score, explaining the assessment based on the resume, transcript, and other analyses. Must be at least 100 words."
        },
        "predictive_success": {
            "type": "integer",
            "description": "A percentage (1-100) representing how successful the candidate might be in the role."
        }
    },
    "required": [
        "raw_score",
        "reason",
        "predictive_success"
    ]
}