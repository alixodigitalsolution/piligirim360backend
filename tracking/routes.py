from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from config import supabase
from auth.rbac import get_current_user

router = APIRouter()


class TrackingPointRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stepsCount: int = 0
    distanceMeters: float = 0
    roundNumber: int = 0
    recordedAt: Optional[str] = None


class StartTrackingRequest(BaseModel):
    trackingType: str


class SyncTrackingRequest(BaseModel):
    sessionId: Optional[str] = None
    trackingType: str
    roundsCompleted: int = 0
    stepsCount: int = 0
    distanceMeters: float = 0
    status: str = "active"
    points: List[TrackingPointRequest] = []


@router.post("/start")
def startTracking(body: StartTrackingRequest, user=Depends(get_current_user)):
    if user.get("role") != "pilgrim":
        raise HTTPException(status_code=403, detail="Only pilgrims can track rituals")
    try:
        data = {
            "pilgrim_id": user["sub"],
            "group_id": _getAgencyId(user["sub"]),
            "tracking_type": body.trackingType,
            "status": "active",
        }
        res = supabase.table("tracking_sessions").insert(data).execute()
        return {"success": True, "data": res.data[0] if res.data else data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
def syncTracking(body: SyncTrackingRequest, user=Depends(get_current_user)):
    if user.get("role") != "pilgrim":
        raise HTTPException(status_code=403, detail="Only pilgrims can sync rituals")
    try:
        sessionId = body.sessionId
        sessionData = {
            "pilgrim_id": user["sub"],
            "group_id": _getAgencyId(user["sub"]),
            "tracking_type": body.trackingType,
            "rounds_completed": body.roundsCompleted,
            "steps_count": body.stepsCount,
            "distance_meters": body.distanceMeters,
            "status": body.status,
        }
        if body.status == "completed":
            sessionData["ended_at"] = datetime.now(timezone.utc).isoformat()

        if sessionId:
            supabase.table("tracking_sessions").update(sessionData).eq("id", sessionId).execute()
        else:
            res = supabase.table("tracking_sessions").insert(sessionData).execute()
            sessionId = res.data[0]["id"] if res.data else None

        pointRows = []
        for point in body.points:
            pointRows.append({
                "session_id": sessionId,
                "pilgrim_id": user["sub"],
                "latitude": point.latitude,
                "longitude": point.longitude,
                "steps_count": point.stepsCount,
                "distance_meters": point.distanceMeters,
                "round_number": point.roundNumber,
                "recorded_at": point.recordedAt or datetime.now(timezone.utc).isoformat(),
            })
        if pointRows:
            supabase.table("tracking_points").insert(pointRows).execute()

        return {"success": True, "session_id": sessionId, "points_synced": len(pointRows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def getTrackingStatus(user=Depends(get_current_user)):
    try:
        res = supabase.table("tracking_sessions") \
            .select("*") \
            .eq("pilgrim_id", user["sub"]) \
            .order("started_at", desc=True) \
            .limit(10) \
            .execute()
        return {"success": True, "data": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _getAgencyId(userId: str):
    res = supabase.table("users_table").select("agency_id").eq("id", userId).limit(1).execute()
    return res.data[0].get("agency_id") if res.data else None
