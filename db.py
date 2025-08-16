import os
from supabase_async import create_client, AsyncClient
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: AsyncClient = create_client(url, key)