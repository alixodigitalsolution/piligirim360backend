# ============================================================
# messaging/routes.py — Group Messaging Endpoints
# ============================================================
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from config import supabase
from auth.rbac import require_any_staff

router = APIRouter()

class SendMessageRequest(BaseModel):
    group_id: str
    leader_id: str | None = None
    message_text: str
    message_type: str = "text"          # "text" | "location_pin"
    pin_latitude: Optional[float] = None
    pin_longitude: Optional[float] = None
    pin_label: Optional[str] = None


@router.post("/send")
def send_message(body: SendMessageRequest, user=Depends(require_any_staff)):
    """Leader sends text message or location pin to all group members."""
    try:
        _ensure_group_access(body.group_id, user)
        data = {
            "group_id": body.group_id,
            "leader_id": user["sub"],
            "message_type": body.message_type,
            "message_text": body.message_text,
        }
        if body.message_type == "location_pin":
            data.update({
                "pin_latitude": body.pin_latitude,
                "pin_longitude": body.pin_longitude,
                "pin_label": body.pin_label or "Meet Here",
                "message_text": f"📍 Meet here: {body.pin_label or 'Leader Location'}",
            })
        res = supabase.table("group_messages").insert(data).execute()
        return {"success": True, "data": res.data[0] if res.data else data}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/group/{group_id}")
def get_messages(group_id: str, limit: int = 50, user=Depends(require_any_staff)):
    """Fetch message history for a group."""
    try:
        _ensure_group_access(group_id, user)
        res = supabase.table("group_messages") \
            .select("*") \
            .eq("group_id", group_id) \
            .order("sent_at", desc=True) \
            .limit(limit) \
            .execute()
        messages = res.data or []
        messages.reverse()   # oldest first for chat display
        return {"success": True, "data": messages}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


class ShareLocationRequest(BaseModel):
    group_id: str
    leader_id: str | None = None
    latitude: float
    longitude: float
    label: Optional[str] = "Leader's Current Location"

@router.post("/share-location")
def share_leader_location(body: ShareLocationRequest, user=Depends(require_any_staff)):
    """Leader shares their live GPS location as a location_pin message."""
    try:
        _ensure_group_access(body.group_id, user)
        data = {
            "group_id": body.group_id,
            "leader_id": user["sub"],
            "message_type": "location_pin",
            "message_text": f"📍 {body.label}",
            "pin_latitude": body.latitude,
            "pin_longitude": body.longitude,
            "pin_label": body.label,
        }
        res = supabase.table("group_messages").insert(data).execute()
        return {"success": True, "data": res.data[0] if res.data else data}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


def _ensure_group_access(group_id: str, user: dict):
    if user.get("role") in ("admin", "super_admin"):
        return
    agency_id = user.get("agency_id")
    if not agency_id:
        res = supabase.table("users_table").select("agency_id").eq("id", user["sub"]).limit(1).execute()
        agency_id = res.data[0].get("agency_id") if res.data else None
    if agency_id and agency_id != group_id:
        raise HTTPException(status_code=403, detail="Access denied for this group")
