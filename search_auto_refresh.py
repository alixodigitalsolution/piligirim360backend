import inspect
from supabase_auth._sync.gotrue_client import SyncGoTrueClient

print("Searching methods referencing _auto_refresh_token or _persist_session...")
for name in dir(SyncGoTrueClient):
    attr = getattr(SyncGoTrueClient, name)
    if inspect.isfunction(attr):
        try:
            src = inspect.getsource(attr)
            if "_auto_refresh_token" in src or "_persist_session" in src or "recover_session" in src:
                print(f"\n--- Method: {name} ---")
                print(src)
        except Exception:
            pass
