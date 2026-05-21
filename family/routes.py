# ============================================================
# family/routes.py — Family Read-Only Tracking Link
# POST   /family/link/generate     — Pilgrim generates family link
# GET    /family/view/{token}       — Public: family views pilgrim location
# DELETE /family/link/{token}       — Pilgrim revokes link
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter()


def get_current_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class GenerateLinkRequest(BaseModel):
    expires_days: Optional[int] = 30  # Default: 30 days


# ── Generate Family Link ───────────────────────────────────
@router.post("/link/generate")
def generate_family_link(body: GenerateLinkRequest, authorization: str = Header(None)):
    """
    Pilgrim generates a unique read-only family tracking link.
    Family opens the URL in any browser — no app or account needed.
    """
    user = get_current_user(authorization)
    user_id = user.get("sub")

    # Revoke any existing active link first
    supabase.table("family_links") \
        .update({"is_active": False}) \
        .eq("user_id", user_id) \
        .eq("is_active", True) \
        .execute()

    token = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(days=body.expires_days)).isoformat()

    link_data = {
        "user_id": user_id,
        "token": token,
        "expires_at": expires_at,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        res = supabase.table("family_links").insert(link_data).execute()
        if res.data:
            return {
                "success": True,
                "message": "Family tracking link generated",
                "token": token,
                "tracking_url": f"/family/view/{token}",
                "expires_at": expires_at,
                "note": "Is link ko apne ghar walon ko bhejein — woh browser mein apka location dekh sakte hain",
            }
        raise HTTPException(status_code=500, detail="Failed to generate link")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Public Family View ─────────────────────────────────────
@router.get("/view/{token}")
def family_view(token: str):
    """
    PUBLIC endpoint — no auth required.
    Family opens this in browser to see pilgrim's live location.
    Returns location, battery %, and check-in status. No name shown (privacy).
    """
    try:
        # Validate token
        link_res = supabase.table("family_links") \
            .select("user_id, expires_at, is_active") \
            .eq("token", token) \
            .limit(1) \
            .execute()

        if not link_res.data:
            raise HTTPException(status_code=404, detail="Link not found or has been revoked")

        link = link_res.data[0]

        if not link["is_active"]:
            raise HTTPException(status_code=410, detail="This tracking link has been revoked")

        # Check expiry
        expires_at = datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=410, detail="This tracking link has expired")

        user_id = link["user_id"]

        # Fetch latest location
        loc_res = supabase.table("pilgrim_locations") \
            .select("latitude, longitude, battery_level, is_online, recorded_at") \
            .eq("pilgrim_id", user_id) \
            .order("recorded_at", desc=True) \
            .limit(1) \
            .execute()

        location = loc_res.data[0] if loc_res.data else None

        # Fetch latest check-in
        checkin_res = supabase.table("checkins") \
            .select("status, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        checkin = checkin_res.data[0] if checkin_res.data else None

        return {
            "success": True,
            "message": "Family tracking view",
            "note": "Privacy protected — pilgrim name not shown",
            "location": location,
            "checkin_status": checkin.get("status") if checkin else None,
            "last_checkin_at": checkin.get("created_at") if checkin else None,
            "link_expires_at": link["expires_at"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Revoke Family Link ─────────────────────────────────────
@router.delete("/link/{token}")
def revoke_family_link(token: str, authorization: str = Header(None)):
    """Pilgrim revokes their family tracking link."""
    user = get_current_user(authorization)
    user_id = user.get("sub")

    try:
        res = supabase.table("family_links") \
            .update({"is_active": False}) \
            .eq("token", token) \
            .eq("user_id", user_id) \
            .execute()

        return {"success": True, "message": "Family tracking link revoked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
