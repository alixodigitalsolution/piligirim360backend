import subprocess
import sys

packages = [
    "fastapi",
    "uvicorn[standard]",
    "supabase",
    "python-dotenv",
    "python-jose[cryptography]",
    "passlib[bcrypt]",
    "pydantic[email]",
    "python-multipart",
    "httpx"
]

print("Starting installation...")
for pkg in packages:
    print(f"Installing {pkg}...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Successfully installed {pkg}")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {pkg}")
        print("Error:", e.stderr)
