from pydantic import BaseModel


class SkillsRequest(BaseModel):  # BaseModel for automatic validation and serialization
    resume_skills: list[str]
    job_skills: list[str]
