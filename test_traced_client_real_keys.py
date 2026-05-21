import os
import time
from dotenv import load_dotenv
from supabase_auth._sync.gotrue_client import SyncGoTrueClient
from supabase_auth._sync.gotrue_base_api import SyncGoTrueBaseAPI
from supabase.lib.client_options import SyncMemoryStorage

class TracedGoTrueClient(SyncGoTrueClient):
    def __init__(self, url, headers, storage):
        print("Tracing: Starting TracedGoTrueClient.__init__")
        
        print("Tracing: calling SyncGoTrueBaseAPI.__init__")
        t = time.time()
        SyncGoTrueBaseAPI.__init__(
            self,
            url=url,
            headers=headers,
            http_client=None,
        )
        print(f"Tracing: SyncGoTrueBaseAPI.__init__ OK in {time.time() - t:.4f}s")
        
        self._jwks = {"keys": []}
        self._jwks_ttl = 600
        self._jwks_cached_at = None
        self._storage_key = "supabase.auth.token"
        self._auto_refresh_token = False
        self._persist_session = False
        self._storage = storage
        self._in_memory_session = None
        self._refresh_token_timer = None
        self._network_retries = 0
        self._state_change_emitters = {}
        self._flow_type = "implicit"
        
        print("Tracing: Instantiating SyncGoTrueAdminAPI")
        t = time.time()
        from supabase_auth._sync.gotrue_admin_api import SyncGoTrueAdminAPI
        self.admin = SyncGoTrueAdminAPI(
            url=self._url,
            headers=self._headers,
            http_client=self._http_client,
        )
        print(f"Tracing: SyncGoTrueAdminAPI OK in {time.time() - t:.4f}s")
        
        print("Tracing: Instantiating SyncGoTrueMFAAPI")
        t = time.time()
        from supabase_auth._sync.gotrue_mfa_api import SyncGoTrueMFAAPI
        self.mfa = SyncGoTrueMFAAPI()
        print(f"Tracing: SyncGoTrueMFAAPI OK in {time.time() - t:.4f}s")
        
        print("Tracing: Setting MFA attributes")
        self.mfa.challenge = self._challenge  # type: ignore
        self.mfa.challenge_and_verify = self._challenge_and_verify  # type: ignore
        self.mfa.enroll = self._enroll  # type: ignore
        self.mfa.get_authenticator_assurance_level = (  # type: ignore
            self._get_authenticator_assurance_level
        )
        self.mfa.list_factors = self._list_factors  # type: ignore
        self.mfa.unenroll = self._unenroll  # type: ignore
        self.mfa.verify = self._verify  # type: ignore
        print("Tracing: MFA attributes OK")
        
        print("Tracing: TracedGoTrueClient.__init__ completed successfully!")

print("Loading .env...")
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print("Instantiating TracedGoTrueClient with real credentials...")
try:
    client = TracedGoTrueClient(
        url=f"{url}/auth/v1",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        storage=SyncMemoryStorage(),
    )
    print("Success instantiating TracedGoTrueClient!")
except Exception as e:
    print(f"Failed: {e}")
