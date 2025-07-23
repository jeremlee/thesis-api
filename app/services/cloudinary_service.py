import cloudinary
import cloudinary.api
import cloudinary.utils
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


async def fetch_file(public_id: str, resource_type: str = "raw"):
    """Fetch file metadata from Cloudinary."""
    try:
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: cloudinary.api.resource(public_id, resource_type=resource_type),
        )
    except Exception as e:
        print(f"Failed with default: {str(e)}")


def generate_signed_url(public_id: str, resource_type: str = "raw") -> str:
    url, _ = cloudinary.utils.cloudinary_url(
        public_id, resource_type=resource_type, sign_url=False, type="upload"
    )
    return url
