import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Let's run a query to get database tables and information if possible, or try querying common table names.
# Common tables might be: users_table, group_assignments, leader_pilgrims, agency_groups, etc.
# Wait, we can run a SQL query via postgrest if we have exec_sql RPC, but earlier we saw RPC exec_sql doesn't exist.
# Let's try to query some suspected table names directly and see if they exist or throw an error.
tables_to_try = ["group_assignments", "leader_pilgrims", "group_codes", "group_members", "pilgrim_groups", "groups"]

for t in tables_to_try:
    try:
        res = supabase.table(t).select("*").limit(1).execute()
        print(f"Table '{t}' exists! Columns: {list(res.data[0].keys()) if res.data else 'empty'}")
    except Exception as e:
        # If it doesn't exist, we'll get an APIError
        pass

# Let's inspect the tables that actually have columns like leader_id or pilgrim_id or group_code
# Wait, we can query information_schema.columns if we can, but postgrest doesn't let us query arbitrary systems tables unless they are exposed.
# Let's do a search for tables in the database by querying a list of tables.
# Wait! Let's write a python script to search the postgres system catalogs by querying supabase.table("pg_tables") or similar if allowed?
# Usually, pg_catalog.pg_tables is not exposed.
# Let's look at the image again:
# Column names: leader_id, pilgrim_id, created_at, group_code.
# Values:
# - Row 1: leader_id=550e8400-e29b-41d4-a716-4466..., pilgrim_id=550e8400-e29b-41d4-a716-4466..., created_at=2026-05-20..., group_code=AG123-334
# - Row 2: leader_id=NULL, pilgrim_id=efefefef..., created_at=2026-05-20..., group_code=AG123-333
# - Row 3: leader_id=NULL, pilgrim_id=1b6e32f5..., created_at=2026-05-20..., group_code=AG123-333
# - Row 4: leader_id=550e8400-e29b-41d4-a716-4466..., pilgrim_id=550e8400-e29b-41d4-a716-4466..., created_at=2026-05-20..., group_code=AG123-334
# - Row 5: leader_id=NULL, pilgrim_id=7d291b52..., created_at=2026-05-20..., group_code=AG123-334
# - Row 6: leader_id=550e8400-e29b-41d4-a716-4466..., pilgrim_id=550e8400-e29b-41d4-a716-4466..., created_at=2026-05-20..., group_code=AG123-334
# - Row 7: leader_id=550e8400-e29b-41d4-a716-4466..., pilgrim_id=NULL, created_at=2026-05-20..., group_code=AG123-333
#
# Wait! Let's search the workspace for where AG123-333 or AG123-334 or AG123 might be generated or used!
