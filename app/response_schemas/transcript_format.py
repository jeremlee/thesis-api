transcript_response_schema = {
    "type": "object",
    "properties": {
        "sentimental_analysis": {
            "type": "string",
            "description": "A detailed sentimental analysis based on the interview transcript, focusing on the overall emotional tone, positive/negative sentiment, and any shifts or nuances in emotion. Must be at least 100 words."
        },
        "personality_traits": {
            "type": "string",
            "description": "A detailed breakdown of the candidate's personality traits based on the interview transcript, covering aspects like openness, conscientiousness, extroversion, agreeableness, and neuroticism (Big Five personality traits). Must be at least 100 words."
        },
        "communication_style_insights": {
            "type": "string",
            "description": "A detailed analysis of the candidate's communication style based on the interview transcript, including examples of styles such as assertive, passive, aggressive, passive-aggressive, empathetic, direct, or indirect. Must be at least 100 words."
        },
        "interview_insights": {
            "type": "string",
            "description": "Key insights extracted from the interview, summarizing overall sentiment, the dominant communication style observed, and notable soft skills demonstrated. This field should provide a concise summary of the most important takeaways from the transcript. Must be at least 100 words."
        },
        "cultural_fit_insights": {
            "type": "string",
            "description": "Key insights extracted from the interview, summarizing and comparing the candidate's values to the company's core values which are: quality,agility, integrity, exceeding customer expectations through innovation, and efficiency."
        }
    },
    "required": [
        "sentimental_analysis",
        "personality_traits",
        "communication_style_insights",
        "interview_insights",
        "cultural_fit_insights"
    ]
}