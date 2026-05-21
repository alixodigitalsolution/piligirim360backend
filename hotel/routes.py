# ============================================================
# hotel/routes.py — Hotel & Transport Info
# POST /hotel/info              — Agency uploads hotel/transport info
# GET  /hotel/info/{org_id}     — Pilgrims fetch hotel info
# PUT  /hotel/info/{org_id}     — Agency updates hotel info
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
from datetime import datetime, timezone
import json

router = APIRouter()


def get_current_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class BusScheduleItem(BaseModel):
    route: str
    departure_time: str
    pickup_point: str
    date: Optional[str] = None


class HotelInfoRequest(BaseModel):
    hotel_name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    room_info: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    hotel_phone: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    bus_number: Optional[str] = None
    bus_schedule: Optional[List[BusScheduleItem]] = None
    madinah_hotel_name: Optional[str] = None
    madinah_hotel_address: Optional[str] = None


@router.post("/info")
def upload_hotel_info(body: HotelInfoRequest, authorization: str = Header(None)):
    """Agency uploads hotel and transport info for pilgrims."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only agency admins can upload hotel info")

    org_id = user.get("agency_id") or user.get("sub")

    schedule_json = [s.dict() for s in body.bus_schedule] if body.bus_schedule else []

    data = {
        "org_id": org_id,
        "hotel_name": body.hotel_name,
        "address": body.address,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "room_info": body.room_info,
        "check_in_date": body.check_in_date,
        "check_out_date": body.check_out_date,
        "hotel_phone": body.hotel_phone,
        "driver_name": body.driver_name,
        "driver_phone": body.driver_phone,
        "bus_number": body.bus_number,
        "bus_schedule": schedule_json,
        "madinah_hotel_name": body.madinah_hotel_name,
        "madinah_hotel_address": body.madinah_hotel_address,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Upsert by org_id
        existing = supabase.table("hotel_info").select("id").eq("org_id", org_id).execute()
        if existing.data:
            res = supabase.table("hotel_info").update(data).eq("org_id", org_id).execute()
        else:
            res = supabase.table("hotel_info").insert(data).execute()

        if res.data:
            return {"success": True, "message": "Hotel info saved successfully", "data": res.data[0]}
        raise HTTPException(status_code=500, detail="Failed to save hotel info")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{org_id}")
def get_hotel_info(org_id: str, authorization: str = Header(None)):
    """Pilgrim fetches hotel and transport info for their agency."""
    get_current_user(authorization)

    try:
        res = supabase.table("hotel_info").select("*").eq("org_id", org_id).limit(1).execute()
        if not res.data:
            return {"success": True, "hotel_info": None, "message": "No hotel info uploaded yet"}
        return {"success": True, "hotel_info": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
