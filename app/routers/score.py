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
)

router = APIRouter(prefix="/score", tags=["Score"])


def flatten_resume(resume_json: dict) -> str:
    """
    Convert resume JSON into a plain text string for embedding.
    Only includes soft_skills, hard_skills, work_experience, and projects.
    """
    parts = []

    # Soft skills
    if "soft_skills" in resume_json:
        parts.append("Soft skills: " + ", ".join(resume_json["soft_skills"]))

    # Hard skills
    if "hard_skills" in resume_json:
        parts.append("Hard skills: " + ", ".join(resume_json["hard_skills"]))

    # Work experience
    if "work_experience" in resume_json:
        for exp in resume_json["work_experience"]:
            title = exp.get("title", "")
            company = exp.get("company", "")
            parts.append(f"{title} at {company}")

    # Projects
    if "projects" in resume_json:
        for proj in resume_json["projects"]:
            name = proj.get("name", "")
            desc = proj.get("description", "")
            parts.append(f"Project {name}: {desc}")

    return "\n".join(parts)


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
):
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
        )
        resume_json = parsed_resume["raw_output"]
        resume_text = flatten_resume(resume_json)
        resume_emb = embedding_model.encode(resume_text, normalize_embeddings=True)
        transcription = transcribed["transcription"]
        transcription_text = " ".join(str(v) for v in transcription.values())
        transcription_emb = embedding_model.encode(
            transcription_text, normalize_embeddings=True
        )
        job_emb = embedding_model.encode(
            requirements_text + "\n" + tags_text, normalize_embeddings=True
        )
        cultural_fit_emb = embedding_model.encode(
            core_values, normalize_embeddings=True
        )

        resume_score = cosine_similarity([resume_emb], [job_emb])[0][0]
        transcription_score = cosine_similarity(
            [transcription_emb], [cultural_fit_emb]
        )[0][0]
        overall_score = (resume_score * 0.7) + (transcription_score * 0.3)

        raw_output = scoring_gemini_model.generate_content(prompt).text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        raw_output = json.loads(raw_output)
        raw_output["raw_score"] = float(round(float(overall_score) * 5, 2))

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

        return {
            "message": "Candidate scored successfully",
            "score_data": convert_objectid(raw_output),
        }
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
