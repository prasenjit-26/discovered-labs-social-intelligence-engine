from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY
    if not url or not key:
        print("Warning: Supabase credentials not found in settings.")
        # Return None or raise error depending on strictness. 
        # For now, we'll let it fail downstream if used.
    return create_client(url, key)

# Singleton instance
supabase = get_supabase_client()
