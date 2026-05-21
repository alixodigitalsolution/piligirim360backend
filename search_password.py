import os

print("Searching for 'password' in python/markdown files...")
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py') or f.endswith('.md') or f.endswith('.txt'):
            try:
                path = os.path.join(root, f)
                with open(path, encoding='utf-8', errors='ignore') as file:
                    for i, line in enumerate(file, 1):
                        line_lower = line.lower()
                        if 'password' in line_lower and any(kw in line_lower for kw in ['=', ':', 'const', 'let', 'str', 'default']):
                            print(f"{path}:{i} -> {line.strip()}")
            except Exception as e:
                pass
