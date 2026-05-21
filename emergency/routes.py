# ============================================================
# emergency/routes.py — SOS Alert Management
# Table: sos_alerts (pilgrim_id, group_id, latitude, longitude,
#                    status, created_at, resolved_at)
# ============================================================
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from config import supabase
from auth.rbac import get_current_user, require_any_staff

router = APIRouter()


# ── Request models ─────────────────────────────────────────
class SosRequest(BaseModel):
    latitude: float
    longitude: float
    batteryLevel: Optional[int] = None


class ResolveRequest(BaseModel):
    notes: Optional[str] = None


# ── Helper: get pilgrim's agency_id ────────────────────────
def _get_agency_id(user_id: str) -> Optional[str]:
    res = supabase.table("users_table") \
        .select("agency_id") \
        .eq("id", user_id) \
        .limit(1) \
        .execute()
    return res.data[0].get("agency_id") if res.data else None


def _enrich_alerts(alerts: list) -> list:
    """Attach pilgrim name/email to each alert."""
    for alert in alerts:
        pid = alert.get("pilgrim_id")
        if pid:
            try:
                ur = supabase.table("users_table") \
                    .select("full_name, email, phone") \
                    .eq("id", pid).limit(1).execute()
                alert["pilgrim"] = ur.data[0] if ur.data else None
            except Exception:
                alert["pilgrim"] = None
    return alerts


# ── POST /emergency/sos — pilgrim triggers SOS ─────────────
@router.post("/sos")
def create_sos_alert(body: SosRequest, user=Depends(get_current_user)):
    """Only pilgrims can create SOS alerts."""
    # Allow any role in an emergency (frontend restricts)
    try:
        agency_id = _get_agency_id(user["sub"])
        data = {
            "pilgrim_id": user["sub"],
            "group_id":   agency_id,
            "latitude":   body.latitude,
            "longitude":  body.longitude,
            "status":     "active",
        }
        res = supabase.table("sos_alerts").insert(data).execute()

        # Also update pilgrim location
        if agency_id:
            supabase.table("pilgrim_locations").upsert({
                "pilgrim_id":   user["sub"],
                "group_id":     agency_id,
                "latitude":     body.latitude,
                "longitude":    body.longitude,
                "battery_level": body.batteryLevel,
                "is_online":    True,
                "recorded_at":  "now()",
            }, on_conflict="pilgrim_id,group_id").execute()

        return {"success": True, "data": res.data[0] if res.data else data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /emergency/sos/active — ALL active alerts (super_admin) ──
@router.get("/sos/active")
def get_active_sos_alerts(
    group_id: Optional[str] = Query(None),
    agency_id: Optional[str] = Query(None),
    user=Depends(require_any_staff)
):
    """
    Returns active SOS alerts.
    - super_admin: all alerts
    - admin: their agency alerts
    - leader: their group alerts
    Pass ?group_id=... or ?agency_id=... to filter.
    """
    try:
        q = supabase.table("sos_alerts") \
            .select("id, pilgrim_id, group_id, latitude, longitude, status, created_at, resolved_at") \
            .order("created_at", desc=True)

        role = user.get("role")

        # If leader role, filter by their group pilgrims
        if role == "leader":
            groups_res = supabase.table("pilgrim_groups").select("group_name").eq("leader_id", user["sub"]).execute()
            group_names = [g["group_name"] for g in (groups_res.data or [])]
            if group_names:
                pilgrims_res = supabase.table("pilgrim_groups").select("pilgrim_id").in_("group_name", group_names).execute()
                pilgrim_ids = [p["pilgrim_id"] for p in (pilgrims_res.data or []) if p.get("pilgrim_id")]
                if pilgrim_ids:
                    q = q.in_("pilgrim_id", pilgrim_ids)
                else:
                    q = q.in_("pilgrim_id", ["00000000-0000-0000-0000-000000000000"])
            else:
                q = q.in_("pilgrim_id", ["00000000-0000-0000-0000-000000000000"])
        # Filter by group_id (leader scope)
        elif group_id:
            q = q.eq("group_id", group_id)
        # Filter by agency_id (admin scope)
        elif agency_id:
            q = q.eq("group_id", agency_id)
        # If admin role, auto-scope to their agency
        elif role == "admin":
            user_agency = _get_agency_id(user["sub"])
            if user_agency:
                q = q.eq("group_id", user_agency)

        res = q.execute()
        alerts = _enrich_alerts(res.data or [])
        active  = [a for a in alerts if a.get("status") == "active"]
        resolved = [a for a in alerts if a.get("status") != "active"]

        return {
            "success": True,
            "data":    alerts,
            "active_count":   len(active),
            "resolved_count": len(resolved),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /emergency/sos/{alert_id} — single alert details ───
@router.get("/sos/{alert_id}")
def get_sos_alert(alert_id: str, user=Depends(require_any_staff)):
    try:
        res = supabase.table("sos_alerts") \
            .select("*") \
            .eq("id", alert_id) \
            .limit(1).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="SOS alert not found")

        alert = res.data[0]
        # Enrich with pilgrim details + medical card
        ur = supabase.table("users_table") \
            .select("full_name, email, phone") \
            .eq("id", alert["pilgrim_id"]).limit(1).execute()
        mr = supabase.table("medical_cards") \
            .select("*") \
            .eq("user_id", alert["pilgrim_id"]).limit(1).execute()

        alert["pilgrim"]      = ur.data[0] if ur.data else None
        alert["medical_card"] = mr.data[0] if mr.data else None
        return {"success": True, "data": alert}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── PUT /emergency/sos/{alert_id}/resolve — resolve an alert ──
@router.put("/sos/{alert_id}/resolve")
def resolve_sos_alert(alert_id: str, body: ResolveRequest = None, user=Depends(require_any_staff)):
    """Mark an SOS alert as resolved (staff only)."""
    try:
        from datetime import datetime, timezone
        update_data = {
            "status":      "resolved",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
        res = supabase.table("sos_alerts") \
            .update(update_data) \
            .eq("id", alert_id) \
            .execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"success": True, "data": res.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /emergency/sos — list all (with optional filter) ───
@router.get("/sos")
def list_sos_alerts(
    status:    Optional[str] = Query(None, description="Filter by status: active|resolved"),
    group_id:  Optional[str] = Query(None),
    agency_id: Optional[str] = Query(None),
    limit:     int            = Query(50, le=200),
    user=Depends(require_any_staff)
):
    try:
        q = supabase.table("sos_alerts") \
            .select("id, pilgrim_id, group_id, latitude, longitude, status, created_at, resolved_at") \
            .order("created_at", desc=True) \
            .limit(limit)

        role = user.get("role")
        if status:
            q = q.eq("status", status)
        if role == "leader":
            groups_res = supabase.table("pilgrim_groups").select("group_name").eq("leader_id", user["sub"]).execute()
            group_names = [g["group_name"] for g in (groups_res.data or [])]
            if group_names:
                pilgrims_res = supabase.table("pilgrim_groups").select("pilgrim_id").in_("group_name", group_names).execute()
                pilgrim_ids = [p["pilgrim_id"] for p in (pilgrims_res.data or []) if p.get("pilgrim_id")]
                if pilgrim_ids:
                    q = q.in_("pilgrim_id", pilgrim_ids)
                else:
                    q = q.in_("pilgrim_id", ["00000000-0000-0000-0000-000000000000"])
            else:
                q = q.in_("pilgrim_id", ["00000000-0000-0000-0000-000000000000"])
        elif group_id:
            q = q.eq("group_id", group_id)
        elif agency_id:
            q = q.eq("group_id", agency_id)
        elif role == "admin":
            user_agency = _get_agency_id(user["sub"])
            if user_agency:
                q = q.eq("group_id", user_agency)

        res = q.execute()
        alerts = _enrich_alerts(res.data or [])
        return {"success": True, "data": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETE /emergency/sos/{alert_id} — delete an alert ────────
@router.delete("/sos/{alert_id}")
def delete_sos_alert(alert_id: str, user=Depends(require_any_staff)):
    """Delete an SOS alert completely from database (staff only)."""
    try:
        res = supabase.table("sos_alerts") \
            .delete() \
            .eq("id", alert_id) \
            .execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"success": True, "message": "Alert deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
