from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()


def get_supabase_client() -> Client:
    """Create and return a Supabase client instance."""
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_anon_key,  # Use service_role_key for admin operations
    )


def get_supabase_admin_client() -> Client:
    """Create and return a Supabase admin client instance with service role key."""
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )
