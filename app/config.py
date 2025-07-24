from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Cloudinary configuration settings."""

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_url: str = ""

    """ Gemini API configuration settings. """
    gemini_api_key: str = ""

    """ Supabase configuration settings. """
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    postgres_url: str = ""
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_database: str = ""
    postgres_host: str = ""
    postgres_prisma_url: str = ""
    postgres_url_non_pooling: str = ""

    """ MongoDB configuration settings. """
    mongodb_uri: str = ""
    database_name: str = ""

    debug: bool = False

    model_config = {"env_file": ".env.local"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
