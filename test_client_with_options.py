import os
import time
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

print("Loading .env...")
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"URL: {url}")
print(f"Key Length: {len(key) if key else 0}")

print("\n--- Instantiating Client with disabled background token refresh & persistence ---")
t0 = time.time()
try:
    options = ClientOptions(auto_refresh_token=False, persist_session=False)
    client = create_client(url, key, options=options)
    print(f"Client instantiated in {time.time() - t0:.4f}s")
except Exception as e:
    print(f"Failed to instantiate: {e}")
    client = None

if client:
    print("\n--- Querying users_table ---")
    t0 = time.time()
    try:
        res = client.table("users_table").select("email").limit(1).execute()
        print(f"Query OK: {res.data} in {time.time() - t0:.4f}s")
    except Exception as e:
        print(f"Query Failed: {e}")
