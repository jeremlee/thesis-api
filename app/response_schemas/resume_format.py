resume_response_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "The full name of the candidate."},
        "city": {
            "type": "string",
            "description": "The current city of residence of the candidate. Put N/A if null",
        },
        "contact_number": {
            "type": "string",
            "description": "The contact phone number of the candidate.",
        },
        "email": {
            "type": "string",
            # Removed format: "email" - not supported by Gemini
            "description": "The email address of the candidate.",
        },
        "educational_background": {
            "type": "array",
            "description": "A list of educational degrees and institutions.",
            "items": {
                "type": "object",
                "properties": {
                    "degree": {
                        "type": "string",
                        "description": "The degree obtained (e.g., Bachelor of Science, Master of Arts).",
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The start date of the education (e.g., 'YYYY-MM', 'YYYY').",
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The end date of the education, or 'Present' if ongoing.",
                    },
                    "institution": {
                        "type": "string",
                        "description": "The name of the educational institution.",
                    },
                },
                "required": ["degree", "institution"],
            },
        },
        "soft_skills": {
            "type": "array",
            "description": "A list of the candidate's soft skills (e.g., communication, teamwork, leadership).",
            "items": {"type": "string"},
        },
        "hard_skills": {
            "type": "array",
            "description": "A list of the candidate's technical or hard skills (e.g., Python, SQL, Project Management).",
            "items": {"type": "string"},
        },
        "work_experience": {
            "type": "array",
            "description": "A list of past work experiences.",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The job title held (e.g., Software Engineer, Project Manager).",
                    },
                    "company": {
                        "type": "string",
                        "description": "The name of the company.",
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The start date of the work experience (e.g., 'YYYY-MM', 'YYYY').",
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The end date of the work experience, or 'Present' if current.",
                    },
                    "description": {
                        "type": "string",
                        "description": "A brief description of responsibilities and achievements in this role.",
                    },
                },
                "required": ["title", "company", "start_date"],
            },
        },
        "projects": {
            "type": "array",
            "description": "A list of personal or professional projects.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the project.",
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The start date of the project (e.g., 'YYYY-MM', 'YYYY').",
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The end date of the project, or 'Present' if ongoing.",
                    },
                    "description": {
                        "type": "string",
                        "description": "A description of the project, including its purpose and your contributions.",
                    },
                },
                "required": ["name", "description"],
            },
        },
    },
    "required": [
        "name",
        "city",
        "contact_number",
        "email",
        "educational_background",
        "soft_skills",
        "hard_skills",
        "work_experience",
        "projects",
    ],
}
