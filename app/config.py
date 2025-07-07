from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Cloudinary configuration settings."""

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    """ Gemini API configuration settings. """
    gemini_api_key: str = ""

    debug: bool = False

    model_config = {"env_file": ".env.local"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
