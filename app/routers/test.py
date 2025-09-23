from fastapi import APIRouter
from app.routers.schemas.test import SkillsRequest
from app.routers.score import cosine_similarity_scoring


router = APIRouter(prefix="/test", tags=["Test"])


@router.post("/")
async def test_endpoint(skills: SkillsRequest) -> dict[str, str]:
    try:
        result = 1 + 4 * cosine_similarity_scoring(skills.resume_skills, skills.job_skills)
        return {"message": str(result)}
    except Exception as e:
        return {"error": str(e)}
