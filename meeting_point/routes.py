# ============================================================
# meeting_point/routes.py — Smart Meeting Point System
# POST /group/meeting-point               — Leader sets meeting point
# GET  /group/meeting-point/{group_id}    — Pilgrims fetch meeting point
# DELETE /group/meeting-point/{group_id}  — Leader clears meeting point
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
import uuid
from datetime import datetime, timezone

router = APIRouter()


def get_current_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class MeetingPointRequest(BaseModel):
    group_id: str
    latitude: float
    longitude: float
    label: str  # e.g. "Gate 79, King Fahd Gate"
    description: Optional[str] = None


# ── Set Meeting Point ──────────────────────────────────────
@router.post("/meeting-point")
def set_meeting_point(body: MeetingPointRequest, authorization: str = Header(None)):
    """
    Leader sets a meeting point on the map.
    All pilgrims in the group will see this pin instantly.
    """
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only group leaders can set meeting points")

    # Upsert: replace existing meeting point for this group
    point_data = {
        "group_id": body.group_id,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "label": body.label,
        "description": body.description,
        "set_by": user.get("sub"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Delete existing point for this group first
        supabase.table("meeting_points").delete().eq("group_id", body.group_id).execute()
        # Insert new one
        res = supabase.table("meeting_points").insert(point_data).execute()
        if res.data:
            return {
                "success": True,
                "message": f"Meeting point set at '{body.label}'",
                "meeting_point": res.data[0],
            }
        raise HTTPException(status_code=500, detail="Failed to set meeting point")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Get Meeting Point ──────────────────────────────────────
@router.get("/meeting-point/{group_id}")
def get_meeting_point(group_id: str, authorization: str = Header(None)):
    """Pilgrims fetch the current meeting point for their group."""
    get_current_user(authorization)  # Any authenticated user can view

    try:
        res = supabase.table("meeting_points") \
            .select("*") \
            .eq("group_id", group_id) \
            .eq("is_active", True) \
            .limit(1) \
            .execute()

        if not res.data:
            return {"success": True, "meeting_point": None, "message": "No meeting point set"}

        return {"success": True, "meeting_point": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Clear Meeting Point ────────────────────────────────────
@router.delete("/meeting-point/{group_id}")
def clear_meeting_point(group_id: str, authorization: str = Header(None)):
    """Leader clears/removes the meeting point."""
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders can clear meeting points")

    try:
        supabase.table("meeting_points").delete().eq("group_id", group_id).execute()
        return {"success": True, "message": "Meeting point cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SetNextRequest(BaseModel):
    group_id: str
    pin_id: Optional[str] = None


@router.post("/destinations")
def add_destination(body: MeetingPointRequest, authorization: str = Header(None)):
    """
    Leader adds a new destination pin for their group.
    """
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only group leaders can add destinations")

    point_data = {
        "group_id": body.group_id,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "label": body.label,
        "description": body.description,
        "set_by": user.get("sub"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        res = supabase.table("meeting_points").insert(point_data).execute()
        if res.data:
            return {
                "success": True,
                "message": f"Destination pin '{body.label}' added successfully.",
                "destination": res.data[0]
            }
        raise HTTPException(status_code=500, detail="Failed to add destination pin")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/destinations/{group_id}")
def get_destinations(group_id: str, authorization: str = Header(None)):
    """
    Pilgrims & leaders fetch all destinations + which one is marked next.
    """
    get_current_user(authorization)

    try:
        # Fetch all active meeting/destination points for this group
        res = supabase.table("meeting_points") \
            .select("*") \
            .eq("group_id", group_id) \
            .eq("is_active", True) \
            .order("created_at", desc=False) \
            .execute()

        # Fetch which pin is marked as the next destination from app_settings table
        next_res = supabase.table("app_settings") \
            .select("setting_value") \
            .eq("setting_key", f"next_destination_{group_id}") \
            .limit(1) \
            .execute()

        next_id = None
        if next_res.data:
            next_id = next_res.data[0].get("setting_value", {}).get("pin_id")

        return {
            "success": True,
            "destinations": res.data or [],
            "next_destination_id": next_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/destinations/{pin_id}")
def delete_destination(pin_id: str, authorization: str = Header(None)):
    """
    Leader removes a specific destination pin.
    """
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders can delete destinations")

    try:
        supabase.table("meeting_points").delete().eq("id", pin_id).execute()
        return {"success": True, "message": "Destination deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/destinations/set-next")
def set_next_destination(body: SetNextRequest, authorization: str = Header(None)):
    """
    Leader sets a specific pin as the group's "Next Destination".
    """
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders can set the next destination")

    try:
        key = f"next_destination_{body.group_id}"
        val = {"pin_id": body.pin_id}
        
        # Save active pin mapping in app_settings
        supabase.table("app_settings").upsert({
            "setting_key": key,
            "setting_value": val,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"success": True, "message": "Next destination milestone set successfully.", "data": val}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
