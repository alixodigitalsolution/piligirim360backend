import bcrypt

# The hash from supabase_combined.sql (same for all seed users)
hash_str = "$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq"
hash_bytes = hash_str.encode('utf-8')

candidates = [
    'password', 'password123', 'Password123', 'pilgrim123', 'Pilgrim123',
    'pilgrim360', 'Pilgrim360', 'admin123', 'Admin123', '12345678',
    'test1234', 'Test1234', 'hajj1234', 'Hajj1234', 'leader123', 'Leader123',
    'pakistan123', 'Pakistan123', 'pilgrim@123', 'Pilgrim@123',
    'Admin@123', 'admin@123', 'Admin@360', 'Pilgrim@360',
    'alixo123', 'Alixo123', 'welcome123', 'Welcome123',
    'testpass', 'qwerty123', '11111111', 'secret123',
    'changeme', 'default123', 'pass1234', 'Pass1234',
]

print(f"Testing {len(candidates)} passwords against hash...")
found = False
for p in candidates:
    try:
        result = bcrypt.checkpw(p.encode('utf-8'), hash_bytes)
        if result:
            print(f"FOUND PASSWORD: '{p}'")
            found = True
            break
        else:
            print(f"  No: {p}")
    except Exception as e:
        print(f"  Error for '{p}': {e}")

if not found:
    print("\nPassword not found in candidate list.")
