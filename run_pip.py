import subprocess
import sys

# Open in line buffered mode
sys.stdout = open('pip_out.txt', 'w', buffering=1, encoding='utf-8')
sys.stderr = sys.stdout

print("Starting streaming pip install...", flush=True)

try:
    process = subprocess.Popen(
        [sys.executable, "-m", "pip", "install", "supabase", "--no-cache-dir"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    for line in process.stdout:
        print(line, end='', flush=True)
        
    process.wait()
    print(f"\nPip process finished with exit code {process.returncode}", flush=True)
except Exception as e:
    print(f"\nException: {e}", flush=True)

sys.stdout.close()
