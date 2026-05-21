# ============================================================
# diary/routes.py — Hajj / Umrah Personal Diary
# POST   /diary/entry              — Add journal entry
# GET    /diary/entries/{user_id}  — List all entries
# DELETE /diary/entry/{id}         — Delete an entry
# GET    /diary/share/{user_id}    — Generate read-only family share link
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
from datetime import datetime, timezone
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


# Reverse geocode labels for known Hajj/Umrah locations
def get_location_label(lat: Optional[float], lng: Optional[float]) -> str:
    if lat is None or lng is None:
        return "Unknown location"

    zones = [
        ((21.42, 21.43), (39.82, 39.83), "Masjid al-Haram ke qareeb"),
        ((21.35, 21.42), (39.84, 39.90), "Makkah Mukarramah mein"),
        ((21.38, 21.41), (39.87, 39.92), "Mina mein"),
        ((21.35, 21.36), (39.98, 40.02), "Arafat mein"),
        ((21.37, 21.39), (39.93, 39.97), "Muzdalifah mein"),
        ((24.46, 24.48), (39.61, 39.63), "Masjid-e-Nabawi ke qareeb"),
        ((24.46, 24.50), (39.58, 39.65), "Madinah Munawwarah mein"),
    ]

    for (lat_range, lng_range, label) in zones:
        if lat_range[0] <= lat <= lat_range[1] and lng_range[0] <= lng <= lng_range[1]:
            return label

    return "Safar mein"


class DiaryEntryRequest(BaseModel):
    text: str
    photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    mood: Optional[str] = None  # e.g., "grateful", "emotional", "tired"


@router.post("/entry")
def add_diary_entry(body: DiaryEntryRequest, authorization: str = Header(None)):
    """Pilgrim adds a personal diary/journal entry."""
    user = get_current_user(authorization)
    user_id = user.get("sub")

    location_label = get_location_label(body.latitude, body.longitude)

    entry_data = {
        "user_id": user_id,
        "text": body.text,
        "photo_url": body.photo_url,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "location_label": location_label,
        "mood": body.mood,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        res = supabase.table("diary_entries").insert(entry_data).execute()
        if res.data:
            return {
                "success": True,
                "message": "Diary entry saved",
                "entry": res.data[0],
                "location_label": location_label,
            }
        raise HTTPException(status_code=500, detail="Failed to save diary entry")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries/{user_id}")
def list_diary_entries(user_id: str, authorization: str = Header(None)):
    """List all diary entries for a pilgrim."""
    user = get_current_user(authorization)

    # Users can only view their own diary (unless leader/admin)
    if user.get("sub") != user_id and user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="You can only view your own diary")

    try:
        res = supabase.table("diary_entries") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .execute()

        return {
            "success": True,
            "user_id": user_id,
            "entries": res.data,
            "total": len(res.data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/entry/{entry_id}")
def delete_diary_entry(entry_id: str, authorization: str = Header(None)):
    """Delete a diary entry."""
    user = get_current_user(authorization)
    user_id = user.get("sub")

    check = supabase.table("diary_entries").select("user_id").eq("id", entry_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Entry not found")

    if check.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own entries")

    supabase.table("diary_entries").delete().eq("id", entry_id).execute()
    return {"success": True, "message": "Diary entry deleted"}


@router.get("/share/{user_id}")
def get_diary_share_summary(user_id: str, authorization: str = Header(None)):
    """Generate a read-only summary of diary for family sharing."""
    get_current_user(authorization)

    try:
        user_res = supabase.table("users_table") \
            .select("full_name, created_at") \
            .eq("id", user_id).limit(1).execute()

        entries_res = supabase.table("diary_entries") \
            .select("text, location_label, created_at, mood") \
            .eq("user_id", user_id) \
            .order("created_at") \
            .execute()

        pilgrim_name = user_res.data[0]["full_name"] if user_res.data else "Pilgrim"

        return {
            "success": True,
            "pilgrim_name": pilgrim_name,
            "total_entries": len(entries_res.data),
            "journey_start": user_res.data[0]["created_at"] if user_res.data else None,
            "entries": entries_res.data,
            "share_note": "Yeh diary family ke sath share karne ke liye hai",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
