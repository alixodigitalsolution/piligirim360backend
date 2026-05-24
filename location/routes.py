# ============================================================
# location/routes.py — Location API Endpoints
# ============================================================
from fastapi import APIRouter, Depends, HTTPException
from config import supabase
from auth.rbac import require_any_staff, require_leader

router = APIRouter()

@router.get("/all")
def get_all_locations(user=Depends(require_any_staff)):
    """
    Super Admin: Returns latest location for ALL pilgrims across all agencies.
    Also includes leaders if they have a location.
    """
    try:
        # Get all latest pilgrim locations
        res = supabase.table("pilgrim_locations") \
            .select("pilgrim_id, group_id, latitude, longitude, battery_level, is_online, recorded_at") \
            .order("recorded_at", desc=True) \
            .limit(2000) \
            .execute()

        # Deduplicate — keep latest per pilgrim
        seen = {}
        for r in (res.data or []):
            pid = r["pilgrim_id"]
            if pid not in seen:
                seen[pid] = r

        # Enrich with user names
        enriched = []
        for loc in seen.values():
            try:
                u = supabase.table("users_table") \
                    .select("full_name, phone, role") \
                    .eq("id", loc["pilgrim_id"]).limit(1).execute()
                if u.data:
                    loc["full_name"] = u.data[0].get("full_name", "Pilgrim")
                    loc["phone"]     = u.data[0].get("phone", "")
                    loc["role"]      = u.data[0].get("role", "pilgrim")
                else:
                    loc["full_name"] = "Pilgrim"
            except Exception:
                loc["full_name"] = "Pilgrim"
            enriched.append(loc)

        return {"success": True, "data": enriched, "count": len(enriched)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/group/{group_id}")
def get_group_locations(
    group_id: str,
    user=Depends(require_any_staff)
):
    """
    Returns latest location for every pilgrim in a group.
    Called by Leader Dashboard every 5 seconds.
    """
    try:
        _ensure_group_access(group_id, user)
        role = user.get("role")
        if role == "leader":
            # 1. Fetch group names for this leader
            groups_res = supabase.table("pilgrim_groups").select("group_name").eq("leader_id", user["sub"]).execute()
            group_names = [g["group_name"] for g in (groups_res.data or [])]
            # 2. Get pilgrim IDs in those groups
            if group_names:
                pilgrims_res = supabase.table("pilgrim_groups").select("pilgrim_id").in_("group_name", group_names).execute()
                pilgrim_ids = [p["pilgrim_id"] for p in (pilgrims_res.data or []) if p.get("pilgrim_id")]
                # Add leader's own ID so they show up on the map too!
                pilgrim_ids.append(user["sub"])
                if pilgrim_ids:
                    res = supabase.table("pilgrim_locations") \
                        .select("pilgrim_id, latitude, longitude, battery_level, is_online, recorded_at") \
                        .eq("group_id", group_id) \
                        .in_("pilgrim_id", pilgrim_ids) \
                        .order("recorded_at", desc=True) \
                        .limit(500) \
                        .execute()
                else:
                    res = type('obj', (object,), {'data': []})()
            else:
                res = type('obj', (object,), {'data': []})()
        else:
            res = supabase.table("pilgrim_locations") \
                .select("pilgrim_id, latitude, longitude, battery_level, is_online, recorded_at") \
                .eq("group_id", group_id) \
                .order("recorded_at", desc=True) \
                .limit(500) \
                .execute()

        # Deduplicate — keep only the latest record per pilgrim
        seen = {}
        latest = []
        for r in (res.data or []):
            pid = r["pilgrim_id"]
            if pid not in seen:
                seen[pid] = True
                latest.append(r)

        # Enrich with user names from users_table
        enriched = []
        for loc in latest:
            try:
                u = _select_user_profile(loc["pilgrim_id"])
                name = u.data[0]["full_name"] if u.data else "Unknown"
                phone = u.data[0].get("phone", "") if u.data else ""
                role = u.data[0].get("role", "pilgrim") if u.data else "pilgrim"
            except Exception:
                name = "Pilgrim"
                phone = ""
                role = "pilgrim"
            loc["full_name"] = name
            loc["phone"] = phone
            loc["role"] = role
            enriched.append(loc)

        return {"success": True, "data": enriched, "count": len(enriched)}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sos-alerts")
def get_active_sos(user=Depends(require_any_staff)):
    """Get all active SOS alerts."""
    try:
        res = supabase.table("sos_alerts") \
            .select("*") \
            .eq("status", "active") \
            .order("created_at", desc=True) \
            .execute()
        alerts = res.data or []
        for alert in alerts:
            try:
                user_res = supabase.table("users_table").select("full_name, email, phone").eq("id", alert["pilgrim_id"]).limit(1).execute()
                medical_res = supabase.table("medical_cards").select("*").eq("user_id", alert["pilgrim_id"]).limit(1).execute()
                alert["pilgrim"] = user_res.data[0] if user_res.data else None
                alert["medical_card"] = medical_res.data[0] if medical_res.data else None
            except Exception:
                alert["pilgrim"] = None
                alert["medical_card"] = None
        return {"success": True, "data": alerts}
    except Exception as e:
        if _is_missing_table_error(e):
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sos-alerts/{alert_id}/resolve")
def resolve_sos(alert_id: str, user=Depends(require_any_staff)):
    """Mark an SOS alert as resolved."""
    try:
        from datetime import datetime, timezone
        res = supabase.table("sos_alerts") \
            .update({"status": "resolved", "resolved_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", alert_id) \
            .execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        if _is_missing_table_error(e):
            raise HTTPException(status_code=404, detail="SOS alerts table is not available")
        raise HTTPException(status_code=500, detail=str(e))
from pydantic import BaseModel


@router.get("/pilgrims")
def get_leader_pilgrims(user=Depends(require_leader)):
    """Return all pilgrims assigned to the current leader's agency."""
    agency_id = _get_user_agency_id(user)
    if not agency_id:
        raise HTTPException(status_code=403, detail="No agency assigned to this leader")
    try:
        users_res = _select_pilgrims_for_agency(agency_id)
        pilgrims = users_res.data or []
        for pilgrim in pilgrims:
            try:
                loc_res = supabase.table("pilgrim_locations") \
                    .select("latitude, longitude, battery_level, is_online, recorded_at") \
                    .eq("pilgrim_id", pilgrim["id"]) \
                    .order("recorded_at", desc=True) \
                    .limit(1) \
                    .execute()
                pilgrim["latest_location"] = loc_res.data[0] if loc_res.data else None
            except Exception:
                pilgrim["latest_location"] = None
        return {"success": True, "data": pilgrims, "count": len(pilgrims)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DangerZoneRequest(BaseModel):
    latitude: float
    longitude: float
    radius_meters: int = 50
    label: str = "Danger Area"

@router.post("/danger_zones")
def create_danger_zone(body: DangerZoneRequest, user=Depends(require_any_staff)):
    """Create a new danger zone for the agency/group."""
    try:
        agency_id = _get_user_agency_id(user)
        if not agency_id:
            raise HTTPException(status_code=403, detail="No agency assigned to this user")
        data = {
            "agency_id": agency_id,
            "leader_id": user["sub"],
            "latitude": body.latitude,
            "longitude": body.longitude,
            "radius_meters": body.radius_meters,
            "label": body.label,
        }
        res = supabase.table("danger_zones").insert(data).execute()
        
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from logger import log_event
        log_event(f"User ({user.get('role')}) marked danger zone at {body.latitude}, {body.longitude}", user_id=user["sub"])
            
        return {"success": True, "data": res.data[0] if res.data else None}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/danger_zones")
def get_danger_zones(user=Depends(require_any_staff)):
    """Get active danger zones with custom visibility rules."""
    try:
        agency_id = _get_user_agency_id(user)
        if not agency_id:
            if user.get("role") == "super_admin":
                res = supabase.table("danger_zones").select("*").execute()
                return {"success": True, "data": res.data or []}
            return {"success": True, "data": []}

        # Fetch all danger zones for this agency
        zones_res = supabase.table("danger_zones").select("*").eq("agency_id", agency_id).execute()
        all_zones = zones_res.data or []

        # Fetch creator details to check roles
        creator_ids = list({z["leader_id"] for z in all_zones if z.get("leader_id")})
        creator_roles = {}
        if creator_ids:
            users_res = supabase.table("users_table").select("id, role").in_("id", creator_ids).execute()
            creator_roles = {u["id"]: u["role"] for u in (users_res.data or [])}

        role = user.get("role")
        if role in ("admin", "super_admin"):
            # Admin sees all danger zones
            return {"success": True, "data": all_zones}

        # For Leaders: visible if created by admin or by leaders sharing same group name
        leader_id = user["sub"]
        
        my_groups_res = supabase.table("pilgrim_groups") \
            .select("group_name") \
            .eq("agency_id", agency_id) \
            .eq("leader_id", leader_id) \
            .execute()
        my_group_names = [g["group_name"] for g in (my_groups_res.data or [])]

        shared_leader_ids = {leader_id}
        if my_group_names:
            shared_res = supabase.table("pilgrim_groups") \
                .select("leader_id") \
                .eq("agency_id", agency_id) \
                .in_("group_name", my_group_names) \
                .execute()
            for row in (shared_res.data or []):
                if row.get("leader_id"):
                    shared_leader_ids.add(row["leader_id"])

        filtered_zones = []
        for zone in all_zones:
            creator_id = zone.get("leader_id")
            creator_role = creator_roles.get(creator_id) if creator_id else None

            # Visible if admin created it or it was created by a leader sharing the same group
            if creator_role in ("admin", "super_admin") or creator_id in shared_leader_ids:
                filtered_zones.append(zone)

        return {"success": True, "data": filtered_zones}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/danger_zones/{zone_id}")
def delete_danger_zone(zone_id: str, user=Depends(require_any_staff)):
    """Delete a danger zone if the user is admin or created it."""
    try:
        agency_id = _get_user_agency_id(user)
        if not agency_id:
            raise HTTPException(status_code=403, detail="No agency assigned to this user")

        # Fetch the zone first to verify ownership/agency
        zone_res = supabase.table("danger_zones").select("*").eq("id", zone_id).execute()
        if not zone_res.data:
            raise HTTPException(status_code=404, detail="Danger zone not found")
        
        zone = zone_res.data[0]
        if zone.get("agency_id") != agency_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this zone")

        role = user.get("role")
        if role not in ("admin", "super_admin") and zone.get("leader_id") != user["sub"]:
            raise HTTPException(status_code=403, detail="Only admins or the creator of this zone can delete it")

        supabase.table("danger_zones").delete().eq("id", zone_id).execute()
        return {"success": True, "message": "Danger zone deleted successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


def _get_user_agency_id(user: dict):
    agency_id = user.get("agency_id")
    if agency_id:
        return agency_id
    try:
        res = supabase.table("users_table").select("agency_id").eq("id", user["sub"]).limit(1).execute()
        return res.data[0].get("agency_id") if res.data else None
    except Exception:
        return None


def _ensure_group_access(group_id: str, user: dict):
    if user.get("role") in ("admin", "super_admin"):
        return
    if _get_user_agency_id(user) != group_id:
        raise HTTPException(status_code=403, detail="Access denied for this group")


def _is_missing_table_error(exc: Exception) -> bool:
    text = str(exc)
    return "PGRST205" in text or "schema cache" in text or "Could not find the table" in text


def _is_missing_phone_error(exc: Exception) -> bool:
    return "users_table.phone does not exist" in str(exc) or "column users_table.phone does not exist" in str(exc)


def _select_user_profile(user_id: str):
    try:
        return supabase.table("users_table").select("full_name, phone, role").eq("id", user_id).limit(1).execute()
    except Exception as e:
        if _is_missing_phone_error(e):
            return supabase.table("users_table").select("full_name, role").eq("id", user_id).limit(1).execute()
        raise


def _select_pilgrims_for_agency(agency_id: str):
    try:
        return supabase.table("users_table") \
            .select("id, full_name, email, phone, created_at") \
            .eq("role", "pilgrim") \
            .eq("agency_id", agency_id) \
            .order("full_name") \
            .execute()
    except Exception as e:
        if _is_missing_phone_error(e):
            return supabase.table("users_table") \
                .select("id, full_name, email, created_at") \
                .eq("role", "pilgrim") \
                .eq("agency_id", agency_id) \
                .order("full_name") \
                .execute()
        raise


from auth.rbac import get_current_user
from pydantic import BaseModel

class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float

@router.post("/update")
def update_user_location(body: LocationUpdateRequest, user=Depends(get_current_user)):
    """Update location of the currently logged-in user (pilgrim or leader)."""
    try:
        from datetime import datetime, timezone
        agency_id = _get_user_agency_id(user)
        row = {
            "pilgrim_id": user["sub"],
            "group_id": agency_id,
            "latitude": body.latitude,
            "longitude": body.longitude,
            "battery_level": 100,
            "is_online": True,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("pilgrim_locations").insert(row).execute()
        return {"success": True, "message": "Location updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
