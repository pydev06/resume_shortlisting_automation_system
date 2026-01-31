from supabase import create_client, Client
from ..core.config import get_settings

_supabase_client: Client = None


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client
