import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any
import json
import re
from typing import List

from scipy.sparse import csr_matrix
from app.dependencies import scoring_gemini_model, scoring_prompt
from app.services.mongodb_service import mongodb
from app.services.supabase_service import get_supabase_admin_client
from app.executor import _executor
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

router = APIRouter(prefix="/score", tags=["Score"])


# Scoring without Gemini
def cosine_similarity_scoring(resume_skills: List[str], job_skills: List[str]):
    corpus: list[str] = [" ".join(resume_skills), " ".join(job_skills)]
    vectorizer = TfidfVectorizer()
    tfidf_matrix: csr_matrix = vectorizer.fit_transform(corpus)  # type: ignore
    original_score = sk_cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    scaled_score = 1 + 4 * original_score
    return scaled_score


# Convert ObjectId to string for JSON serialization from MongoDB
def convert_objectid(obj):
    from bson import ObjectId

    if obj is None:
        return None
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    return obj


@router.post("/")
async def score_candidate(user_id: str, job_id: str, applicant_id: str) -> Any:
    try:
        job_listing_data, transcribed, parsed_resume = await asyncio.gather(
            asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: get_supabase_admin_client()
                .table("job_listings")
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

        tags = [
            tag["tags"]["name"]
            for tag in tags.data
            if "tags" in tag and "name" in tag["tags"]
        ]

        raw_score = 0.0
        if not parsed_resume:
            parsed_resume = {"raw_output": "No parsed resume available"}
        else:
            raw_output = parsed_resume.get("raw_output", {})
            user_skills = raw_output.get("hard_skills", []) + raw_output.get(
                "soft_skills", []
            )
            raw_score = cosine_similarity_scoring(user_skills, tags)

        prompt = (
            scoring_prompt
            + "\n Job: "
            + str(job_listing_data.data.get("title", "No title found"))
            + "\nResume: "
            + str(parsed_resume.get("raw_output", "No resume data found"))
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

        raw_output = scoring_gemini_model.generate_content(prompt).text.strip()
        if raw_output.startswith("```json"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        raw_output = json.loads(raw_output)
        raw_output["raw_score"] = float(round(raw_score, 2))

        inserted_id = await mongodb.insert_document(
            "scored_candidates",
            {
                "user_id": user_id,
                "job_id": job_id,
                "score_data": raw_output,
            },
        )

        if not inserted_id:
            raise HTTPException(status_code=500, detail="Failed to insert score data")

        result = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: get_supabase_admin_client()
            .table("job_applicants")
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
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model output was not valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
