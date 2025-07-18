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


async def fetch_file(public_id: str):
    """Fetch file metadata from Cloudinary."""
    try:
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: cloudinary.api.resource(public_id),
        )
    except Exception as e:
        print(f"Failed with default: {str(e)}")

        try:
            print("Trying resource_type='raw'...")
            return await asyncio.get_running_loop().run_in_executor(
                _executor,
                lambda: cloudinary.api.resource(public_id, resource_type="raw"),
            )
        except Exception as e2:
            print(f"Failed with raw: {str(e2)}")

            try:
                print("Trying resource_type='video'...")
                return await asyncio.get_running_loop().run_in_executor(
                    _executor,
                    lambda: cloudinary.api.resource(public_id, resource_type="video"),
                )
            except Exception as e3:
                print(f"Failed with video: {str(e3)}")
                raise Exception(
                    f"Error fetching file with all resource types: {str(e)}"
                )


def generate_signed_url(public_id: str, resource_type: str = "raw") -> str:
    url, _ = cloudinary.utils.cloudinary_url(
        public_id, resource_type=resource_type, sign_url=True, type="upload"
    )
    return url
