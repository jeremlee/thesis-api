import asyncio

from fastapi import APIRouter, HTTPException
from supabase import Client

from app.services.supabase_service import get_supabase_admin_client
from entities.fastapi.joined import JobListingWithRelations

router = APIRouter(prefix="/test", tags=["Test"])


@router.post("/")
async def test_endpoint():
    supabase_client: Client = get_supabase_admin_client()

    try:
        response = await asyncio.to_thread(
            lambda: (
                supabase_client.table("job_listings")
                .select("*, jl_requirements(*), job_tags(*, tags(*))")
                .single()
                .execute()
                .data
            )
        )

        job_listing: JobListingWithRelations = JobListingWithRelations.model_validate(
            response
        )
        return {
            "job_listing_tags": job_listing,
        }
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
