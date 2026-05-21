# ============================================================
# slots/routes.py — Jamarat Timing Slot System
# POST /group/slots/jamarat       — Agency assigns Jamarat slots
# GET  /group/slots/{user_id}     — Pilgrim fetches their assigned slot
# PUT  /group/slots/{slot_id}     — Leader updates a slot
# GET  /group/slots/group/{group_id} — Leader views all group slots
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
from datetime import datetime, timezone
import uuid

router = APIRouter()

VALID_SLOTS = [
    "Morning (7:00 AM - 9:00 AM)",
    "Midday (12:00 PM - 2:00 PM)",
    "Afternoon (3:00 PM - 5:00 PM)",
    "Evening (6:00 PM - 8:00 PM)",
    "Night (9:00 PM - 11:00 PM)",
]


def get_current_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class JamaratSlotRequest(BaseModel):
    user_id: str
    group_id: str
    date: str         # e.g., "2025-06-11" (11 Zil Hajj)
    time_from: str    # e.g., "14:00"
    time_to: str      # e.g., "15:00"
    slot_label: str   # e.g., "Midday (12:00 PM - 2:00 PM)"
    notes: Optional[str] = None


class BulkSlotRequest(BaseModel):
    group_id: str
    slots: List[JamaratSlotRequest]


@router.post("/jamarat")
def assign_jamarat_slot(body: JamaratSlotRequest, authorization: str = Header(None)):
    """Agency or leader assigns a Jamarat time slot to a pilgrim."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin", "leader"]:
        raise HTTPException(status_code=403, detail="Only leaders/admins can assign slots")

    slot_data = {
        "user_id": body.user_id,
        "group_id": body.group_id,
        "date": body.date,
        "time_from": body.time_from,
        "time_to": body.time_to,
        "slot_label": body.slot_label,
        "notes": body.notes,
        "assigned_by": user.get("sub"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Remove existing slot for this user on this date, then insert new
        supabase.table("jamarat_slots") \
            .delete() \
            .eq("user_id", body.user_id) \
            .eq("date", body.date) \
            .execute()

        res = supabase.table("jamarat_slots").insert(slot_data).execute()
        if res.data:
            return {
                "success": True,
                "message": f"Jamarat slot assigned: {body.date} — {body.slot_label}",
                "slot": res.data[0],
            }
        raise HTTPException(status_code=500, detail="Failed to assign slot")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
def get_pilgrim_slots(user_id: str, authorization: str = Header(None)):
    """Pilgrim fetches all their assigned Jamarat time slots."""
    get_current_user(authorization)

    try:
        res = supabase.table("jamarat_slots") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("date") \
            .execute()

        slots = res.data or []

        # Add crowd tip per slot
        crowd_tips = {
            "Morning": "Subah ka waqt nisbatan kam bheed hoti hai — achha waqt hai.",
            "Midday": "Dopahar mein bahut garmi hoti hai — pani saath rakhein.",
            "Afternoon": "Dopahar baad ka waqt zyada mahfooz hai — garmi kum hoti hai.",
            "Evening": "Shaam ko thori bheed hoti hai — apne saathi saath rakhein.",
            "Night": "Raat ka waqt nisbatan zyada theek hota hai — roshandani kafi hoti hai.",
        }

        for slot in slots:
            label = slot.get("slot_label", "")
            for key, tip in crowd_tips.items():
                if key.lower() in label.lower():
                    slot["crowd_tip"] = tip
                    break

        return {
            "success": True,
            "user_id": user_id,
            "slots": slots,
            "total_days": len(slots),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/group/{group_id}")
def get_group_slots(group_id: str, authorization: str = Header(None)):
    """Leader views all Jamarat slots assigned in their group."""
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders can view group slots")

    try:
        res = supabase.table("jamarat_slots") \
            .select("*, users_table:users_table!jamarat_slots_user_id_fkey(full_name, phone)") \
            .eq("group_id", group_id) \
            .order("date") \
            .execute()

        return {"success": True, "group_id": group_id, "slots": res.data, "count": len(res.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{slot_id}")
def update_slot(slot_id: str, body: JamaratSlotRequest, authorization: str = Header(None)):
    """Leader updates an existing Jamarat slot."""
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders can update slots")

    update_data = {
        "date": body.date,
        "time_from": body.time_from,
        "time_to": body.time_to,
        "slot_label": body.slot_label,
        "notes": body.notes,
    }

    try:
        res = supabase.table("jamarat_slots").update(update_data).eq("id", slot_id).execute()
        if res.data:
            return {"success": True, "message": "Slot updated", "slot": res.data[0]}
        raise HTTPException(status_code=404, detail="Slot not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
