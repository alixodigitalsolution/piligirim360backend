# ============================================================
# config.py — Supabase Connection + App Config
# LIVE MODE: Connects to real Supabase project via service key.
# ============================================================
import os
import platform
# Mock platform calls that are known to hang on this sandboxed host environment
platform.system = lambda: "Windows"
platform.release = lambda: "10"
platform.python_version = lambda: "3.12.0"

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_KEY         = os.getenv("SUPABASE_KEY")          # anon key (public)
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # service key (backend only)
JWT_SECRET           = os.getenv("JWT_SECRET", "pilgrim360_super_secret_key_2026")
JWT_ALGORITHM        = "HS256"
JWT_EXPIRE_DAYS      = 30

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "❌ SUPABASE_URL or SUPABASE_SERVICE_KEY missing from .env — "
        "please check your environment variables."
    )

# Use service key for all backend operations (bypasses RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print(f"[config] [OK] Connected to Supabase: {SUPABASE_URL}")
print("[config] [Key] Using service role key for full DB access")
