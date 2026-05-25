import bcrypt
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# ── New password to set ────────────────────────────────────
NEW_PASSWORD = "Admin123"
ADMIN_EMAIL  = "admin@pilgrim360.com"

# Hash the new password
hashed = bcrypt.hashpw(NEW_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

print(f"Resetting password for: {ADMIN_EMAIL}")
print(f"New password:           {NEW_PASSWORD}")
print(f"New hash:               {hashed}")

# Connect and update
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
res = supabase.table("users_table") \
    .update({"password_hash": hashed}) \
    .eq("email", ADMIN_EMAIL) \
    .execute()

if res.data:
    print("\n[SUCCESS] Password reset successfully!")
    print(f"   Email:    {ADMIN_EMAIL}")
    print(f"   Password: {NEW_PASSWORD}")
else:
    print("\n[FAILED] Update failed - no matching row found.")
    print(res)
