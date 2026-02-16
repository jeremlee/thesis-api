import re
import json
import asyncio
from fastapi import APIRouter, HTTPException, Query
from sklearn.metrics.pairwise import cosine_similarity

from app.services.mongodb_service import mongodb
from app.services.supabase_service import get_supabase_admin_client
from app.executor import _executor
from app.dependencies import (
    localized_scoring_prompt,
    embedding_model,
    core_values,
    scoring_gemini_model,
    soft_skills_baseline,
)
from app.response_schemas.score_format import ScoreCandidateResponse
from pydantic import BaseModel
router = APIRouter(prefix="/score", tags=["Score"])


class JobFitData(BaseModel):
    hard_skills: str
    work_experiences: str
    projects: str
class PredictiveSuccessData(BaseModel):
    soft_skills: str
    transcription: str

def get_jobfitdata(resume_json: dict) -> JobFitData:
    
    hard_skills = ""
    if "hard_skills" in resume_json:
        hard_skills = "Technical Competencies: " + ", ".join(resume_json["hard_skills"])

    work_experiences = ""
    if "work_experience" in resume_json:
        exp_parts = [
            f"Role: {e.get('title')} at {e.get('company')}. Responsibilities and Tech: {e.get('description', '')}"
            for e in resume_json["work_experience"]
        ]
        work_experiences = "\n".join(exp_parts)

    projects = ""
    if "projects" in resume_json:
        proj_parts = [
            f"Project: {p.get('name')}. Details: {p.get('description', '')}"
            for p in resume_json["projects"]
        ]
        projects = "\n".join(proj_parts)

    return JobFitData(
        hard_skills=hard_skills,
        work_experiences=work_experiences,
        projects=projects
    )


def get_predictivesuccessdata(resume_json: dict, transcription_data: str) -> PredictiveSuccessData:
    soft_skills = ""
    if "soft_skills" in resume_json:
        soft_skills = "Behavioral Competencies: " + ", ".join(resume_json["soft_skills"])

    return PredictiveSuccessData(
        soft_skills=soft_skills,
        transcription=transcription_data
    )



# def flatten_resume(resume_json: dict) -> str:
#     """
#     Convert resume JSON into a plain text string for embedding.
#     Only includes soft_skills, hard_skills, work_experience, and projects.
#     """
#     parts = []

#     # Soft skills
#     if "soft_skills" in resume_json:
#         parts.append("Soft skills: " + ", ".join(resume_json["soft_skills"]))

#     # Hard skills
#     if "hard_skills" in resume_json:
#         parts.append("Hard skills: " + ", ".join(resume_json["hard_skills"]))

#     # Work experience
#     if "work_experience" in resume_json:
#         for exp in resume_json["work_experience"]:
#             title = exp.get("title", "")
#             company = exp.get("company", "")
#             parts.append(f"{title} at {company}")

#     # Projects
#     if "projects" in resume_json:
#         for proj in resume_json["projects"]:
#             name = proj.get("name", "")
#             desc = proj.get("description", "")
#             parts.append(f"Project {name}: {desc}")

#     return "\n".join(parts)


# Convert ObjectId to string for JSON serialization from MongoDB
def convert_objectid(obj):
    from bson import ObjectId

    match obj:
        case None:
            return None
        case ObjectId():
            return str(obj)
        case dict():
            return {k: convert_objectid(v) for k, v in obj.items()}
        case list():
            return [convert_objectid(item) for item in obj]

    return obj


@router.post("/")
async def score_candidate(
    user_id: str = Query(..., description="User ID"),
    job_id: str = Query(..., description="Job ID"),
    applicant_id: str = Query(..., description="Applicant ID"),
) -> ScoreCandidateResponse:
    supabase_client = get_supabase_admin_client()
    try:
        job_listing_data, transcribed, parsed_resume = await asyncio.gather(
            asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: supabase_client.table("job_listings")
                .select("title")
                .eq("id", job_id)
                .single()
                .execute(),
            ),
            mongodb.find_document(
                "transcribed",
                {"user_id": user_id},
            ),
            mongodb.find_document(
                "parsed_resume",
                {"user_id": user_id},
            ),
        )

        if not job_listing_data:
            raise HTTPException(status_code=404, detail="Job listing not found")

        if not transcribed:
            transcribed = {
                "transcription": {
                    "transcription": "No transcription available",
                    "sentimental_analysis": "No sentimental analysis found",
                    "personality_traits": "No personality traits found",
                    "communication_style_insights": "No communication style insights found",
                    "interview_insights": "No interview insights found",
                }
            }

        tags = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("job_tags")
            .select("*, tags(*)")
            .eq("joblisting_id", job_id)
            .execute(),
        )

        requirements_response = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("jl_requirements")
            .select("requirement")
            .eq("joblisting_id", job_id)
            .execute(),
        )

        tag_list = [t["tags"]["name"] for t in tags.data]
        tags_text = "Tags: " + ", ".join(tag_list)

        # Requirements: extract the 'requirement' field
        requirements_list = [r["requirement"] for r in requirements_response.data]
        requirements_text = "Requirements: " + "; ".join(requirements_list)

        tags = [
            str(tag["tags"]["name"])
            for tag in tags.data
            if "tags" in tag and "name" in tag["tags"]
        ]
        if not parsed_resume:
            raise HTTPException(status_code=404, detail="Parsed resume not found for this user")
        resume_json = parsed_resume["raw_output"]
        transcription = transcribed["transcription"]
        # format transcription data
        transcription_text = " ".join(str(v) for v in transcription.values())
        jobfitdata: JobFitData = get_jobfitdata(resume_json)
        predictivesuccessdata: PredictiveSuccessData = get_predictivesuccessdata(resume_json, transcription_text)
        # converts hard skills, work experiences, projects to numerical vector
        jobfit_text = (
            f"TECHNICAL SKILLS:\n{jobfitdata.hard_skills}\n\n"
            f"PROFESSIONAL EXPERIENCE:\n{jobfitdata.work_experiences}\n\n"
            f"TECHNICAL PROJECTS:\n{jobfitdata.projects}"
        )
        jobfit_emb = embedding_model.encode(jobfit_text, normalize_embeddings=True)

        # converts soft skills to numerical vector
        softskills_text = (
            f"SOFT SKILLS:\n{predictivesuccessdata.soft_skills}\n\n"
        )
        softskills_emb = embedding_model.encode(softskills_text, normalize_embeddings=True)
        #converts transcription to numerical vector
        transcription_text = (
            f"TRANSCRIPTION:\n{predictivesuccessdata.transcription}\n\n"
        )
        transcription_emb = embedding_model.encode(transcription_text, normalize_embeddings=True)
        # converts job requirements text and tags to numerical vector
        job_emb = embedding_model.encode(
            requirements_text + "\n" + tags_text, normalize_embeddings=True
        )
        # converts the company's core values to numerical vector
        cultural_fit_emb = embedding_model.encode(
            core_values, normalize_embeddings=True
        )
        soft_skills_baseline_emb = embedding_model.encode(
            soft_skills_baseline, normalize_embeddings=True
        )
        # THE NUMERICAL VECTORS WILL BE USED TO COMPUTE THE SCORES THROUGH COSINE SIMILARITY

        # computes the cosine similarity between the jobfitdata (hard skills, work experiences and projects) and the job requirements 

        # take note that job_fit_score was previously referred to as raw_score

        job_fit_score = cosine_similarity([jobfit_emb], [job_emb])[0][0]

        # computes the cosine similarity between the soft skills and the soft skills standard 

        soft_skills_score = cosine_similarity([softskills_emb], [soft_skills_baseline_emb])[0][0]

        # computes the cosine similarity between the transcription data and the soft skills standard 

        transcription_score = cosine_similarity([transcription_emb], [soft_skills_baseline_emb])[0][0]

        # computes the cosine similarity between the soft skills and the cultural fit

        cultural_fit_score = cosine_similarity([softskills_emb], [cultural_fit_emb])[0][0]

        # computes the cosine similarity between the transcription data and the cultural fit

        transcription_cultural_fit_score = cosine_similarity([transcription_emb], [cultural_fit_emb])[0][0]

        # 1. Calculate the Behavioral Blend (The "How they work" side)

        # We prioritize the transcription (interview) over the resume list
        behavioral_blend = (
            (transcription_cultural_fit_score * 0.30) + 
            (transcription_score * 0.25) + 
            (cultural_fit_score * 0.15) + 
            (soft_skills_score * 0.30)
        )

        # normalizing values
        # will be stored in raw_output 
        soft_skills_score_pct = min(100, int((soft_skills_score / 0.85) * 100))
        transcription_score_pct = min(100, int((transcription_score / 0.85) * 100))
        cultural_fit_score_pct = min(100, int((cultural_fit_score / 0.85) * 100))
        trans_cultural_fit_score_pct = min(100, int((transcription_cultural_fit_score / 0.85) * 100))

        # 2. Calculate Final Predictive Success (50% Job Fit + 50% Behavior)

        # This results in a value between 0.0 and 1.0

        predictive_success_raw = (job_fit_score * 0.40) + (behavioral_blend * 0.60)

        # 3. Scaling for Human Readability

        # Since MPNet scores rarely hit 1.0, we scale the result.

        # A raw score of 0.80 should probably look like a 95% to a recruiter.

        predictive_success_final_score = min(100, int((predictive_success_raw / 0.85) * 100))

        # 4. Job Fit Score (1-5 Star Rating)

        # Similarly, we scale 0.85 similarity to be a 5-star result. 0.85 is the perfect score
        job_fit_final_score = min(100, int((job_fit_score / 0.85) * 100))
        job_fit_stars = round(min(5.0, (job_fit_score / 0.85) * 5), 1)

        """
        scores are based from:
        job fit score (previously raw_score) = hard skills from resume, work experiences, projects
        predictive success = soft skills from resume, transcription, cultural fit
        """

        # PROMPT SECTION
        prompt = (
            localized_scoring_prompt
            + "\n Job: "
            + str(job_listing_data.data.get("title", "No title found"))
            + "\nResume: "
            + str(parsed_resume.get("raw_output", "No resume data found"))
            + "\nJob Tags: "
            + ", ".join(tags)
            + "\nTranscript: "
            + str(
                transcribed.get("transcription", {}).get(
                    "transcription", "No transcription data found"
                )
            )
            + "\n--- Candidate Analysis ---"
            + "\nSentimental Analysis: "
            + str(
                transcribed.get("transcription", {}).get(
                    "sentimental_analysis", "No sentimental analysis found"
                )
            )
            + "\nPersonality Traits: "
            + str(
                transcribed.get("transcription", {}).get(
                    "personality_traits", "No personality traits found"
                )
            )
            + "\nCommunication Style Insights: "
            + str(
                transcribed.get("transcription", {}).get(
                    "communication_style_insights",
                    "No communication style insights found",
                )
            )
            + "\nInterview Insights: "
            + str(
                transcribed.get("transcription", {}).get(
                    "interview_insights", "No interview insights found"
                )
            )
            + "CALCULATED SCORES BY COSINE SIMILARITY: \n"
            + f"JOB_FIT_SCORE = {job_fit_final_score}\n" 
            + f"PREDICTIVE_SUCCESS_SCORE = {predictive_success_final_score}"
        )

        raw_output = scoring_gemini_model.generate_content(prompt).text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        raw_output = json.loads(raw_output)

        # use these for success likelihood "visualization"
        raw_output["soft_skills_score"] = soft_skills_score_pct
        raw_output["transcription_score"] = transcription_score_pct
        raw_output["transcription_cultural_fit_score"] = trans_cultural_fit_score_pct
        raw_output["cultural_fit_score"] = cultural_fit_score_pct

        # adding the scores to the field
        # final scores
        raw_output["predictive_success"] = predictive_success_final_score
        raw_output["job_fit_score"] = job_fit_final_score
        raw_output["job_fit_stars"] = job_fit_stars

        inserted_id = await mongodb.insert_document(
            "scored_candidates",
            {
                "user_id": user_id,
                "job_id": job_id,
                "score_data": raw_output,
            },
        )

        if not inserted_id:
            await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: supabase_client.table("job_applicants")
                .delete()
                .eq("id", applicant_id)
                .execute(),
            )
            raise HTTPException(status_code=500, detail="Failed to insert score data")

        result = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: supabase_client.table("job_applicants")
            .update({"score_id": str(inserted_id)})
            .eq("id", applicant_id)
            .execute(),
        )

        if not result.data:
            await mongodb.delete_document("scored_candidates", {"_id": inserted_id})
            raise HTTPException(
                status_code=500, detail="Failed to update job applicant"
            )

        return ScoreCandidateResponse(
            message="Candidate scored successfully",
            score_data=convert_objectid(raw_output),
        )
    except Exception as e:
        await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: supabase_client.table("job_applicants")
            .delete()
            .eq("id", applicant_id)
            .execute(),
        )
        pass

        # surface a clear HTTP error
        raise HTTPException(status_code=500, detail=str(e))
