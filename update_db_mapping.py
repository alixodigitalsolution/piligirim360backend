import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

try:
    print("Updating leader and pilgrim details in users_table...")
    
    # 1. Update leader (Billal) phone number
    leader_id = "0568ccf6-a974-4bd7-9c39-d38819b8838c"
    res_l = supabase.table("users_table").update({
        "phone": "+923001234567"
    }).eq("id", leader_id).execute()
    print("Updated leader phone number successfully!")
    
    # 2. Update pilgrim 1 (Billal2) phone number and leader mapping
    pilgrim1_id = "5f5a3d95-0571-4069-9963-e350366082d6"
    res_p1 = supabase.table("users_table").update({
        "phone": "+923129876543",
        "leader_id": leader_id
    }).eq("id", pilgrim1_id).execute()
    print("Updated pilgrim 1 phone and leader mapping successfully!")
    
    # 3. Update pilgrim 2 (Test) phone number and leader mapping
    pilgrim2_id = "5811cc55-835f-4655-9485-0f631ba22594"
    res_p2 = supabase.table("users_table").update({
        "phone": "+923155554444",
        "leader_id": leader_id
    }).eq("id", pilgrim2_id).execute()
    print("Updated pilgrim 2 phone and leader mapping successfully!")

    print("\n[SUCCESS] All DB mappings, leader assignment, and phone numbers are set!")

except Exception as e:
    print("Error updating database mapping:", e)
