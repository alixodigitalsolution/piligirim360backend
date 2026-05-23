# ============================================================
# auth/login.py — Login Endpoint + JWT Generation
# POST /auth/login
# ============================================================
from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from config import supabase, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_DAYS
from auth.rbac import get_current_user

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Request model ──────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class JourneyRequest(BaseModel):
    journey_type: str

# ── Helpers ────────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    """Verify plaintext vs bcrypt hash."""
    if not hashed:
        return False
    try:
        import bcrypt
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        if hashed.startswith("$2"):
            try:
                return pwd_context.verify(plain, hashed)
            except Exception:
                return False
        # Fallback: plain text comparison (dev mode only)
        return plain == hashed

def create_access_token(user_id: str, role: str, full_name: str, agency_id: str | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "role": role,
        "full_name": full_name,
        "exp": expire,
    }
    if agency_id:
        payload["agency_id"] = agency_id
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ── Login Endpoint ─────────────────────────────────────────
@router.post("/login")
def login(body: LoginRequest):
    """
    Unified login for Leader & Super Admin.
    Returns JWT token + role so frontend can route correctly.
    """
    email = body.email.strip().lower()
    password = body.password



    # ── Security & Validation ───────────────────────────
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security Alert: Password must be at least 8 characters long"
        )
    if "@" not in email or "." not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Query user by email
    try:
        res = supabase.table("users_table") \
            .select("id, email, password_hash, role, full_name, agency_id, journey_type") \
            .eq("email", email) \
            .limit(1) \
            .execute()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication Failed: No account registered with {email}"
        )

    user = res.data[0]

    # Verify password
    if not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication Failed: The password you entered is incorrect"
        )

    # Role-based access control (RBAC)
    allowed_roles = ["pilgrim", "leader", "super_admin", "admin"]
    if user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: The portal is not available for '{user['role']}' role"
        )

    token = create_access_token(
        user["id"],
        user["role"],
        user.get("full_name", ""),
        user.get("agency_id"),
    )

    return {
        "success": True,
        "token": token,
        "role": user["role"],
        "user_id": user["id"],
        "full_name": user.get("full_name", ""),
        "agency_id": user.get("agency_id"),
        "journey_type": user.get("journey_type"),
    }


@router.put("/journey")
def update_journey(body: JourneyRequest, user=Depends(get_current_user)):
    journey = body.journey_type.strip().lower()
    if journey not in ["hajj", "umrah"]:
        raise HTTPException(status_code=400, detail="Journey must be 'hajj' or 'umrah'")

    try:
        res = supabase.table("users_table") \
            .update({"journey_type": journey}) \
            .eq("id", user["sub"]) \
            .execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save journey: {str(e)}")

    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True, "journey_type": journey}


# ── Register endpoint (for seeding test users) ────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str          # "leader" | "super_admin"
    agency_id: str = None

@router.post("/register")
def register(body: RegisterRequest):
    """Create a Leader or Admin account."""
    allowed = ["leader", "super_admin"]
    if body.role not in allowed:
        raise HTTPException(400, "Role must be 'leader' or 'super_admin'")

    import bcrypt
    pwd_bytes = body.password.encode('utf-8')[:72]
    hashed_pw = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode('utf-8')
    data = {
        "email": body.email.strip().lower(),
        "password_hash": hashed_pw,
        "full_name": body.full_name,
        "role": body.role,
        "agency_id": body.agency_id,
    }
    try:
        res = supabase.table("users_table").insert(data).execute()
        if res.data:
            return {"success": True, "user_id": res.data[0]["id"]}
        raise HTTPException(500, "Failed to create user")
    except Exception as e:
        raise HTTPException(500, str(e))


# ── New Pilgrim Self-Registration Flow ────────────────────
@router.get("/check-email")
def check_email(email: str):
    email = email.strip().lower()
    try:
        res = supabase.table("users_table").select("id").eq("email", email).execute()
        return {"exists": len(res.data) > 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify-group")
def verify_group(code: str):
    code = code.strip()
    if not code:
        return {"valid": False, "message": "Group Code cannot be empty."}

    try:
        # Check in pilgrim_groups by group_code column
        res = supabase.table("pilgrim_groups") \
            .select("group_name, leader_id, agency_id") \
            .eq("group_code", code) \
            .execute()

        if not res.data:
            return {"valid": False, "message": "Group Code not found."}

        # Find the row with leader_id assigned to resolve the leader
        leader_row = next((r for r in res.data if r.get("leader_id")), res.data[0])
        leader_id = leader_row.get("leader_id")
        leader_name = "Assigned Leader"
        if leader_id:
            leader_res = supabase.table("users_table") \
                .select("full_name") \
                .eq("id", leader_id) \
                .limit(1) \
                .execute()
            if leader_res.data:
                leader_name = leader_res.data[0]["full_name"]

        return {
            "valid": True,
            "group_name": leader_row["group_name"],
            "leader_name": leader_name,
            "agency_id": leader_row["agency_id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PilgrimRegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    group_code: str
    phone: str | None = None


@router.get("/me")
def get_current_user_profile(user=Depends(get_current_user)):
    """
    Returns full user profile for the currently authenticated user.
    For pilgrims, also returns their leader's name and phone number.
    """
    user_id = user["sub"]
    try:
        res = supabase.table("users_table") \
            .select("id, email, full_name, role, agency_id, leader_id, phone, journey_type") \
            .eq("id", user_id) \
            .limit(1) \
            .execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="User not found")

        profile = res.data[0]

        # For pilgrims, fetch leader info
        if profile.get("leader_id"):
            try:
                leader_res = supabase.table("users_table") \
                    .select("full_name, phone") \
                    .eq("id", profile["leader_id"]) \
                    .limit(1) \
                    .execute()
                if leader_res.data:
                    profile["leader_name"] = leader_res.data[0].get("full_name", "")
                    profile["leader_phone"] = leader_res.data[0].get("phone", "")
                else:
                    profile["leader_name"] = None
                    profile["leader_phone"] = None
            except Exception:
                profile["leader_name"] = None
                profile["leader_phone"] = None
        else:
            profile["leader_name"] = None
            profile["leader_phone"] = None

        # Fetch agency name
        if profile.get("agency_id"):
            try:
                agency_res = supabase.table("agencies") \
                    .select("name") \
                    .eq("id", profile["agency_id"]) \
                    .limit(1) \
                    .execute()
                if agency_res.data:
                    profile["agency_name"] = agency_res.data[0].get("name", "")
                else:
                    profile["agency_name"] = None
            except Exception:
                profile["agency_name"] = None
        else:
            profile["agency_name"] = None

        return {"success": True, "data": profile}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register-pilgrim")
def register_pilgrim(body: PilgrimRegisterRequest):
    email = body.email.strip().lower()
    group_code = body.group_code.strip()

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        # Check duplicate email
        existing = supabase.table("users_table").select("id").eq("email", email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="An account with this email already exists")

        # Lookup group details using group_code
        group_res = supabase.table("pilgrim_groups") \
            .select("group_name, agency_id, leader_id") \
            .eq("group_code", group_code) \
            .execute()

        if not group_res.data:
            raise HTTPException(status_code=400, detail="Invalid or non-existent group code")

        # Find the row with leader_id assigned to resolve the leader
        leader_row = next((r for r in group_res.data if r.get("leader_id")), group_res.data[0])
        agency_id = leader_row["agency_id"]
        leader_id = leader_row.get("leader_id")
        group_name = leader_row["group_name"]

        # Hash password
        import bcrypt
        pwd_bytes = body.password.encode('utf-8')[:72]
        hashed_pw = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode('utf-8')

        pilgrim_id = str(uuid.uuid4())
        user_data = {
            "id": pilgrim_id,
            "email": email,
            "password_hash": hashed_pw,
            "full_name": body.full_name,
            "role": "pilgrim",
            "agency_id": agency_id,
            "leader_id": leader_id,
            "phone": body.phone,
            "journey_type": None
        }

        # Create user
        supabase.table("users_table").insert(user_data).execute()

        # Add to pilgrim_groups
        supabase.table("pilgrim_groups").insert({
            "group_name": group_name,
            "agency_id": agency_id,
            "leader_id": leader_id,
            "pilgrim_id": pilgrim_id,
            "group_code": group_code
        }).execute()

        # Create empty medical card
        supabase.table("medical_cards").insert({
            "user_id": pilgrim_id,
            "blood_type": "O+",
            "allergies": "",
            "medications": "",
            "medical_history": "",
            "emergency_contact_name": "",
            "emergency_contact_phone": "",
        }).execute()

        # Auto-login: generate JWT access token
        token = create_access_token(
            pilgrim_id,
            "pilgrim",
            body.full_name,
            agency_id
        )

        return {
            "success": True,
            "token": token,
            "role": "pilgrim",
            "user_id": pilgrim_id,
            "full_name": body.full_name,
            "agency_id": agency_id,
            "journey_type": None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register pilgrim: {str(e)}")

