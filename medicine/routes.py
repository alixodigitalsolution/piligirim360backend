# ============================================================
# medicine/routes.py — Medicine Reminder System
# POST   /medicine/add              — Pilgrim adds a medicine
# GET    /medicine/list/{user_id}   — List all medicines
# DELETE /medicine/{id}             — Remove a medicine
# POST   /medicine/taken/{id}       — Mark dose as taken
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
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


VALID_FREQUENCIES = ["morning", "afternoon", "evening", "night", "morning_night", "thrice_daily", "custom"]


class MedicineRequest(BaseModel):
    medicine_name: str
    dose: str                        # e.g., "1 tablet", "5ml"
    frequency: str                   # morning | afternoon | evening | night | thrice_daily
    reminder_times: List[str]        # e.g., ["08:00", "14:00", "20:00"]
    notes: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class MarkTakenRequest(BaseModel):
    scheduled_time: str  # Which dose time was taken


@router.post("/add")
def add_medicine(body: MedicineRequest, authorization: str = Header(None)):
    """Pilgrim adds a medicine with reminder schedule."""
    user = get_current_user(authorization)
    user_id = user.get("sub")

    data = {
        "user_id": user_id,
        "medicine_name": body.medicine_name,
        "dose": body.dose,
        "frequency": body.frequency,
        "times": body.reminder_times,
        "notes": body.notes,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        res = supabase.table("medicines").insert(data).execute()
        if res.data:
            return {
                "success": True,
                "message": f"'{body.medicine_name}' reminder set — {', '.join(body.reminder_times)}",
                "medicine": res.data[0],
            }
        raise HTTPException(status_code=500, detail="Failed to add medicine")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{user_id}")
def list_medicines(user_id: str, authorization: str = Header(None)):
    """List all medicines for a pilgrim. Leaders can view for their pilgrims."""
    user = get_current_user(authorization)

    if user.get("sub") != user_id and user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this pilgrim's medicines")

    try:
        res = supabase.table("medicines") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("is_active", True) \
            .order("created_at") \
            .execute()

        now_time = datetime.now(timezone.utc).strftime("%H:%M")

        medicines = res.data or []
        for med in medicines:
            times = med.get("times", [])
            next_reminder = None
            for t in sorted(times):
                if t > now_time:
                    next_reminder = t
                    break
            if not next_reminder and times:
                next_reminder = sorted(times)[0] + " (kal)"
            med["next_reminder"] = next_reminder

        return {
            "success": True,
            "user_id": user_id,
            "medicines": medicines,
            "count": len(medicines),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{medicine_id}")
def delete_medicine(medicine_id: str, authorization: str = Header(None)):
    """Remove a medicine from reminder list."""
    user = get_current_user(authorization)
    user_id = user.get("sub")

    check = supabase.table("medicines").select("user_id, medicine_name").eq("id", medicine_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Medicine not found")

    if check.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own medicines")

    supabase.table("medicines").delete().eq("id", medicine_id).execute()
    return {"success": True, "message": f"'{check.data[0]['medicine_name']}' removed from reminders"}


@router.post("/taken/{medicine_id}")
def mark_dose_taken(medicine_id: str, body: MarkTakenRequest, authorization: str = Header(None)):
    """Pilgrim marks a dose as taken — 'Li li hai' button."""
    user = get_current_user(authorization)
    user_id = user.get("sub")

    # Log the dose taken
    log_data = {
        "user_id": user_id,
        "type": "INFO",
        "message": f"Dawai li: medicine_id={medicine_id}, waqt={body.scheduled_time}",
        "delivered": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        supabase.table("notifications_log").insert(log_data).execute()
        return {
            "success": True,
            "message": "Dose recorded — JazakAllah Khair",
            "taken_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
