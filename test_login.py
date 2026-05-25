import urllib.request
import json

url = "http://localhost:8001/auth/login"
data = {
    "email": "admin@pilgrim360.com",
    "password": "Admin123"
}
req = urllib.request.Request(
    url, 
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Body:", response.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("HTTP Error Status:", e.code)
    print("HTTP Error Body:", e.read().decode("utf-8"))
except Exception as e:
    print("Other Error:", e)
