import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

try:
    print("--- USERS TABLE ---")
    res = supabase.table("users_table").select("*").execute()
    users = res.data
    for u in users:
        print(f"ID: {u['id']}")
        print(f"  Email:      {u['email']}")
        print(f"  Role:       {u['role']}")
        print(f"  Name:       {u['full_name']}")
        print(f"  Phone:      {u['phone']}")
        print(f"  Agency ID:  {u['agency_id']}")
        print(f"  Leader ID:  {u['leader_id']}")
        print(f"  Journey:    {u['journey_type']}")
        print("-" * 30)

    print("\n--- AGENCIES TABLE ---")
    res_a = supabase.table("agencies").select("*").execute()
    agencies = res_a.data
    for a in agencies:
        print(f"ID: {a['id']}")
        print(f"  Name: {a['name']}")
        print(f"  City: {a['city']}")
        print("-" * 30)

except Exception as e:
    print("Error querying database:", e)
