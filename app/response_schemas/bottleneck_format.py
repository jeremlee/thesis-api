bottleneck_response_schema = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "A very short description of the identified process bottleneck. Must be no more than 5 words.",
        },
        "full_description": {
            "type": "string",
            "description": "A detailed and thorough explanation of the process bottleneck, including where it occurs, why it happens, its impact on efficiency, and potential contributing factors. Must be at least 100 words.",
        },
        "category": {
            "type": "string",
            "enum": ["interview", "pipeline", "screening"],
            "description": "The process area where the bottleneck occurs. Must be one of: interview, pipeline, screening.",
        },
        "date": {
            "type": "string",
            "description": "The date when the bottleneck was identified. Must follow the format MM/YY/DD.",
            "pattern": "^(0[1-9]|1[0-2])/\\d{2}/(0[1-9]|[12]\\d|3[01])$",
        },
        "time": {
            "type": "string",
            "description": "The time when the bottleneck was identified. Must follow the format HH:MM (24-hour clock).",
            "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$",
        },
    },
    "required": [
        "description",
        "full_description",
        "category",
        "date",
        "time",
    ],
}
