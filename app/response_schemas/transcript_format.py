transcript_response_schema = {
    "type": "object",
    "properties": {
        "sentimental_analysis": {
            "type": "string",
            "description": "A detailed sentimental analysis based on the interview transcript, focusing on overall emotional tone, positive or negative sentiment, and emotional nuances. Must be at least 100 words."
        },
        "sentimental_analysis_phrases": {
            "type": "array",
            "description": "An array of key phrases summarizing the sentimental analysis. Each phrase must be no more than 7 words.",
            "items": {"type": "string"}
        },

        "personality_traits": {
            "type": "string",
            "description": "A detailed breakdown of the candidate's personality traits based on the interview transcript, including Big Five personality traits. Must be at least 100 words."
        },
        "personality_traits_phrases": {
            "type": "array",
            "description": "An array of key phrases summarizing the candidate's personality traits. Each phrase must be no more than 7 words.",
            "items": {"type": "string"}
        },

        "communication_style_insights": {
            "type": "string",
            "description": "A detailed analysis of the candidate's communication style based on the interview transcript. Must be at least 100 words."
        },
        "communication_style_insights_phrases": {
            "type": "array",
            "description": "An array of key phrases summarizing the communication style insights. Each phrase must be no more than 7 words.",
            "items": {"type": "string"}
        },

        "interview_insights": {
            "type": "string",
            "description": "Key insights extracted from the interview, summarizing sentiment, communication style, and soft skills. Must be at least 100 words."
        },
        "interview_insights_phrases": {
            "type": "array",
            "description": "An array of key phrases summarizing the interview insights. Each phrase must be no more than 7 words.",
            "items": {"type": "string"}
        },

        "cultural_fit_insights": {
            "type": "string",
            "description": "Insights comparing the candidate's values with the company's core values: quality, agility, integrity, innovation, and efficiency."
        },
        "cultural_fit_insights_phrases": {
            "type": "array",
            "description": "An array of key phrases summarizing cultural fit alignment. Each phrase must be no more than 7 words.",
            "items": {"type": "string"}
        }
    },
    "required": [
        "sentimental_analysis",
        "sentimental_analysis_phrases",
        "personality_traits",
        "personality_traits_phrases",
        "communication_style_insights",
        "communication_style_insights_phrases",
        "interview_insights",
        "interview_insights_phrases",
        "cultural_fit_insights",
        "cultural_fit_insights_phrases"
    ]
}
