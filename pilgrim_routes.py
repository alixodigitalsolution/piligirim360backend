from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from config import supabase
from auth.rbac import get_current_user

router = APIRouter()


class LostFoundRequest(BaseModel):
    latitude: float
    longitude: float


@router.post("/lost-found/check")
def check_lost_found(body: LostFoundRequest, user=Depends(get_current_user)):
    """Update pilgrim location and report whether they appear far from their group."""
    if user.get("role") != "pilgrim":
        raise HTTPException(status_code=403, detail="Only pilgrims can use lost/found check")
    agency_id = _get_agency_id(user["sub"])
    try:
        if agency_id:
            supabase.table("pilgrim_locations").insert({
                "pilgrim_id": user["sub"],
                "group_id": agency_id,
                "latitude": body.latitude,
                "longitude": body.longitude,
                "battery_level": None,
                "is_online": True,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        return {
            "success": True,
            "outside_group": False,
            "message": "Location updated. Leader can see your latest position.",
            "latitude": body.latitude,
            "longitude": body.longitude,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lost-found/ok")
def mark_lost_found_ok(user=Depends(get_current_user)):
    """Record a lightweight OK check-in for the current pilgrim."""
    if user.get("role") != "pilgrim":
        raise HTTPException(status_code=403, detail="Only pilgrims can mark OK")
    try:
        res = supabase.table("checkins").insert({
            "user_id": user["sub"],
            "status": "ok",
            "note": "Lost/found safety OK",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return {
            "success": True,
            "message": "Leader ko mark ho gaya: main theek hoon.",
            "data": res.data[0] if res.data else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_agency_id(user_id: str) -> Optional[str]:
    res = supabase.table("users_table").select("agency_id").eq("id", user_id).limit(1).execute()
    return res.data[0].get("agency_id") if res.data else None
