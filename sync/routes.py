from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
from datetime import datetime, timezone
from config import supabase
from auth.rbac import get_current_user

router = APIRouter()


class SyncItem(BaseModel):
    actionType: str
    payload: Dict[str, Any]
    createdAt: str | None = None


class BatchSyncRequest(BaseModel):
    items: List[SyncItem]


@router.post("/batch")
def batchSync(body: BatchSyncRequest, user=Depends(get_current_user)):
    try:
        results = []
        for index, item in enumerate(body.items):
            try:
                result = _processSyncItem(user["sub"], item)
                results.append({"index": index, "success": True, "result": result})
            except Exception as e:
                results.append({"index": index, "success": False, "error": str(e)})
        return {
            "success": True,
            "total": len(body.items),
            "synced": len([r for r in results if r["success"]]),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _processSyncItem(userId: str, item: SyncItem):
    supabase.table("sync_queue").insert({
        "user_id": userId,
        "action_type": item.actionType,
        "payload": item.payload,
        "synced": True,
        "created_at": item.createdAt or datetime.now(timezone.utc).isoformat(),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    if item.actionType == "location_update":
        return _insertLocation(userId, item.payload)
    if item.actionType == "sos_alert":
        return _insertSos(userId, item.payload)
    if item.actionType == "tracking_point":
        return _insertTrackingPoint(userId, item.payload)
    if item.actionType == "update_medical_card":
        return _updateMedicalCard(userId, item.payload)
    return {"stored": True}


def _updateMedicalCard(userId: str, payload: Dict[str, Any]):
    row = {
        "user_id": userId,
        "blood_type": payload.get("blood_type") or payload.get("bloodType"),
        "allergies": payload.get("allergies"),
        "medications": payload.get("medications"),
        "medical_history": payload.get("medical_history") or payload.get("medicalHistory"),
        "emergency_contact_name": payload.get("emergency_contact_name") or payload.get("emergencyContactName"),
        "emergency_contact_phone": payload.get("emergency_contact_phone") or payload.get("emergencyContactPhone"),
        "passport_number": payload.get("passport_number") or payload.get("passportNumber"),
        "visa_number": payload.get("visa_number") or payload.get("visaNumber"),
        "visa_qr_data": payload.get("visa_qr_data") or payload.get("visaQrData"),
        "photo_url": payload.get("photo_url") or payload.get("photoUrl"),
    }
    res = supabase.table("medical_cards").upsert(row, on_conflict="user_id").execute()
    return res.data[0] if res.data else row


def _insertLocation(userId: str, payload: Dict[str, Any]):
    agencyId = _getAgencyId(userId)
    row = {
        "pilgrim_id": userId,
        "group_id": agencyId,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "battery_level": payload.get("batteryLevel"),
        "is_online": True,
        "recorded_at": payload.get("recordedAt") or datetime.now(timezone.utc).isoformat(),
    }
    res = supabase.table("pilgrim_locations").insert(row).execute()
    return res.data[0] if res.data else row


def _insertSos(userId: str, payload: Dict[str, Any]):
    row = {
        "pilgrim_id": userId,
        "group_id": _getAgencyId(userId),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "status": "active",
        "created_at": payload.get("createdAt") or datetime.now(timezone.utc).isoformat(),
    }
    res = supabase.table("sos_alerts").insert(row).execute()
    return res.data[0] if res.data else row


def _insertTrackingPoint(userId: str, payload: Dict[str, Any]):
    row = {
        "session_id": payload.get("sessionId"),
        "pilgrim_id": userId,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "steps_count": payload.get("stepsCount", 0),
        "distance_meters": payload.get("distanceMeters", 0),
        "round_number": payload.get("roundNumber", 0),
        "recorded_at": payload.get("recordedAt") or datetime.now(timezone.utc).isoformat(),
    }
    res = supabase.table("tracking_points").insert(row).execute()
    return res.data[0] if res.data else row


def _getAgencyId(userId: str):
    res = supabase.table("users_table").select("agency_id").eq("id", userId).limit(1).execute()
    return res.data[0].get("agency_id") if res.data else None
