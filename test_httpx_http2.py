import httpx
import time

print("Initializing httpx Client with HTTP/2 enabled...")
t0 = time.time()
try:
    with httpx.Client(http2=True) as client:
        print(f"Client initialized in {time.time() - t0:.4f}s")
except Exception as e:
    print(f"Failed: {e}")
