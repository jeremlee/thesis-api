chatbot_schema = {
    "type": "object",
    "properties": {
        "reply": {
            "type": "string",
            "description": "Reply must be between 5 and 100 words"
        }
    },
    "required": ["reply"],
}
