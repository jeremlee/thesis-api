from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Gemini API configuration settings."""

    gemini_api_key: str = ""

    """ Supabase configuration settings. """
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_base_url: str = ""
    supabase_database_url: str = ""

    model_config = {"env_file": ".env.local"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
