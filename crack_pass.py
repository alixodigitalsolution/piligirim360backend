import bcrypt

# The hash from supabase_combined.sql (same for all seed users)
hash_str = "$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq"
hash_bytes = hash_str.encode('utf-8')

candidates = [
    # Original list
    'password', 'password123', 'Password123', 'pilgrim123', 'Pilgrim123',
    'pilgrim360', 'Pilgrim360', 'admin123', 'Admin123', '12345678',
    'test1234', 'Test1234', 'hajj1234', 'Hajj1234', 'leader123', 'Leader123',
    'pakistan123', 'Pakistan123', 'pilgrim@123', 'Pilgrim@123',
    'Admin@123', 'admin@123', 'Admin@360', 'Pilgrim@360',
    'alixo123', 'Alixo123', 'welcome123', 'Welcome123',
    'testpass', 'qwerty123', '11111111', 'secret123',
    'changeme', 'default123', 'pass1234', 'Pass1234',
    # Extended list
    'Admin360', 'admin360', 'Pilgrim360!', 'admin@pilgrim360', 'Admin@Pilgrim360',
    'superadmin', 'SuperAdmin', 'superadmin123', 'SuperAdmin123',
    'hajj2026', 'Hajj2026', 'umrah2026', 'Umrah2026',
    'P@ssw0rd', 'p@ssw0rd', 'Passw0rd', 'passw0rd',
    'pilgrim2026', 'Pilgrim2026', 'makkah123', 'Makkah123',
    'admin2026', 'Admin2026', 'Test@123', 'test@123',
    '123456789', '1234567890', 'abcd1234', 'Abcd1234',
    'letmein', 'letmein123', 'Letmein123',
    'master123', 'Master123', 'hello123', 'Hello123',
    'welcome1', 'Welcome1', 'password1', 'Password1',
    'adminpass', 'AdminPass', 'kaaba123', 'Kaaba123',
    'mecca123', 'Mecca123', 'makkah2026', 'Makkah2026',
    # More variations
    'Hajj@2026', 'hajj@2026', 'P360Admin', 'p360admin',
    'Pilgrim1', 'pilgrim1', 'Admin1234', 'admin1234',
    'Zam@2026', 'zam@2026', 'Islamic123', 'islamic123',
    'HajjAdmin', 'hajjadmin', 'umrah123', 'Umrah123',
    'system123', 'System123', 'root1234', 'Root1234',
    'toor1234', 'qwerty1234', 'Qwerty1234',
    'abc12345', 'Abc12345', 'ilovehajj', 'IloveHajj',
    'adminadmin', 'AdminAdmin', 'testtest', 'TestTest',
    'pakistan1', 'Pakistan1', 'karachi123', 'Karachi123',
    'lahore123', 'Lahore123', 'islamabad123', 'Islamabad123',
    'P@ssword1', 'p@ssword1', 'Passw0rd1', 'passw0rd1',
    'Admin@2026', 'admin@2026', 'Pass@123', 'pass@123',
    'Hajj1447', 'hajj1447', 'Umrah1447', 'umrah1447',
    'pilgrim!123', 'Pilgrim!123', 'admin!123', 'Admin!123',
    'superpass', 'SuperPass', 'superpass123', 'SuperPass123',
]

print(f"Testing {len(candidates)} passwords against hash...")
found = False
for p in candidates:
    try:
        result = bcrypt.checkpw(p.encode('utf-8'), hash_bytes)
        if result:
            print(f"\n*** FOUND PASSWORD: '{p}' ***\n")
            found = True
            break
        else:
            print(f"  No: {p}")
    except Exception as e:
        print(f"  Error for '{p}': {e}")

if not found:
    print("\nPassword not found in candidate list.")
    print("The password may have been set differently from the seed script.")
    print("Consider resetting it via the /auth/register endpoint.")
