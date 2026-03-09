from pydantic import BaseModel

from app.response_schemas.transcript_format import TranscriptFormat


class ScoreCandidateFormat(BaseModel):
    reason: str
    phrases: list[str]
    skill_gaps_recommendations: str


class ScoredCandidateData(ScoreCandidateFormat):
    soft_skills_score: int
    transcription_score: int
    transcription_cultural_fit_score: int
    cultural_fit_score: int
    response_time: float
    predictive_success: int
    job_fit_score: int
    job_fit_stars: float


class TranscribedData(TranscriptFormat):
    transcription: str


class EducationalBackgroundItem(BaseModel):
    degree: str
    institution: str
    start_date: str | None = None
    end_date: str | None = None


class WorkExperienceItem(BaseModel):
    title: str
    company: str
    start_date: str
    end_date: str | None = None
    description: str | None = None


class ProjectItem(BaseModel):
    name: str
    description: str
    start_date: str | None = None
    end_date: str | None = None


class ParsedResumeData(BaseModel):
    name: str
    city: str
    contact_number: str
    email: str
    educational_background: list[EducationalBackgroundItem]
    soft_skills: list[str]
    hard_skills: list[str]
    work_experience: list[WorkExperienceItem]
    projects: list[ProjectItem]
