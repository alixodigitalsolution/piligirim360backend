import bcrypt
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Passwords by role
passwords = {
    "super_admin": "Admin123",
    "admin": "Admin123",
    "leader": "Leader123",
    "pilgrim": "Pilgrim123"
}

# Fetch all users
try:
    print("Fetching users from database...")
    res = supabase.table("users_table").select("id, email, role").execute()
    users = res.data
    
    if not users:
        print("No users found in users_table.")
        exit(0)
        
    print(f"Found {len(users)} users. Hashing and resetting passwords...")
    
    # Pre-calculate hashes to avoid doing it multiple times
    hashes = {}
    for role, pwd in passwords.items():
        hashes[role] = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
    for user in users:
        uid = user["id"]
        email = user["email"]
        role = user["role"]
        
        # Determine password and hash to use
        pwd = passwords.get(role, "Pilgrim123")
        pwd_hash = hashes.get(role, hashes["pilgrim"])
        
        # Update user password in the table
        supabase.table("users_table").update({"password_hash": pwd_hash}).eq("id", uid).execute()
        print(f"Reset {email} ({role}) password to: '{pwd}'")
        
    print("\n[SUCCESS] All user passwords successfully reset and verified!")

except Exception as e:
    print("An error occurred during password reset:", e)
