# db.py
import os
from supabase import create_client, Client # <<< MUDANÇA CRUCIAL AQUI
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# A função é a mesma, e o cliente retornado pode ser usado com `await`.
# O tipo do cliente é `Client`.
supabase: Client = create_client(url, key)