import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    res = supabase.table("users_table").select("*").eq("full_name", "Hammad").execute()
    print("User table rows:")
    for row in res.data:
        print(f"ID: {row['id']} | Name: {row['full_name']} | Role: {row['role']} | Leader ID: {row.get('leader_id')} | Agency ID: {row.get('agency_id')}")
        if row.get("leader_id"):
            l_res = supabase.table("users_table").select("full_name").eq("id", row["leader_id"]).execute()
            print("  Leader Name:", l_res.data)
except Exception as e:
    print("Error:", e)
