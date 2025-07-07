import cloudinary
import cloudinary.api
import asyncio
from app.config import get_settings
from app.executor import _executor

settings = get_settings()

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


async def fetch_file(public_id: str):
    """Fetch file metadata from Cloudinary."""

    try:
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: cloudinary.api.resource(public_id, resource_type="raw"),
        )
    except Exception as e:
        raise Exception(f"Error fetching file: {str(e)}")
