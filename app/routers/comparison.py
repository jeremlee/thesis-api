import asyncio
import json
import re
import warnings
from fastapi import APIRouter, HTTPException
from typing import Any

from app.services.mongodb_service import mongodb
from app.services.supabase_service import get_supabase_admin_client
from app.executor import _executor
from app.dependencies import localized_comparison_prompt, get_gemma_pipe, GEMMA_SEMAPHORE
from app.executor import _executor
from app.services.mongodb_service import mongodb
from app.services.supabase_service import get_supabase_admin_client
from transformers import Pipeline

router = APIRouter(prefix="/compare_candidate", tags=["Compare Candidate"])

#concept

async def compare_candidates(applicant1_id: str, applicant2_id: str, job_id: str) -> Any: 
    supabase_client = get_supabase_admin_client()
    try:
        #applicant1 data
        job_listing_data, transcribed1, parsed_resume1 = await asyncio.gather(
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
                {"user_id": applicant1_id},
            ),
            mongodb.find_document(
                "parsed_resume",
                {"user_id": applicant1_id},
            ),
        )
        #applicant2 data
        job_listing_data, transcribed2, parsed_resume2 = await asyncio.gather(
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
                {"user_id": applicant2_id},
            ),
            mongodb.find_document(
                "parsed_resume",
                {"user_id": applicant2_id},
            ),
        )

        prompt = localized_comparison_prompt + """\n
            APPLICANT 1: #name of applicant here
            data from the scoring table, blablbal
            APPLICANT 2: #name of applicant here
            data from the scoring table blablabla
        """
        pipe: Pipeline = await get_gemma_pipe()

        async with GEMMA_SEMAPHORE:
            raw_output = await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: pipe(
                    prompt,
                    max_new_tokens=800,
                    return_full_text=False,
                ),
            )


    except Exception as e:
        pass