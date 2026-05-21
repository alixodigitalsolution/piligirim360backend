import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lfapukryvodmubnaszfd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # service key for backend REST calls

url = f"{SUPABASE_URL}/rest/v1/users_table?select=email,role,password_hash"
req = urllib.request.Request(url)
req.add_header("apikey", SUPABASE_KEY)
req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        for user in data:
            print(f"Email: {user['email']}, Role: {user['role']}, Password Hash: {user['password_hash']}")
except Exception as e:
    print("Error:", e)
