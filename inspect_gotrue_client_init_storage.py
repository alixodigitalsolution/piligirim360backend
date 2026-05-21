import os
import supabase_auth

path = os.path.join(os.path.dirname(supabase_auth.__file__), "_sync", "gotrue_client.py")
print(f"Reading {path}...")

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "initialize_from_storage" in line:
        print(f"\nLine {i+1}:")
        # Print 5 lines before and 5 lines after
        start = max(0, i - 5)
        end = min(len(lines), i + 6)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].rstrip()}")
