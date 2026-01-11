import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Institutional Path Management: Locate .env in the project root
# Matches pattern in app/services/fedex.py
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials missing from .env")
    return create_client(url, key)