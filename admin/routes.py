# ============================================================
# admin/routes.py — Super Admin Panel Endpoints
# ============================================================
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config import supabase
from auth.rbac import require_admin
from datetime import datetime, timedelta, timezone
import time

router = APIRouter()


@router.get("/stats")
def get_global_stats(user=Depends(require_admin)):
    """
    Returns platform-wide statistics for the Super Admin panel:
    - Total travel agencies
    - Total registered users
    - Currently online users (updated_at within last 10 min)
    - Active SOS alerts
    """
    try:
        # Total agencies
        agencies_res = supabase.table("agencies") \
            .select("id", count="exact").execute()
        total_agencies = agencies_res.count or 0

        # Total users
        users_res = supabase.table("users_table") \
            .select("id", count="exact").execute()
        total_users = users_res.count or 0

        # Online users — pilgrims with a location update in last 10 minutes
        from datetime import datetime, timedelta, timezone
        ten_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        online_res = supabase.table("pilgrim_locations") \
            .select("pilgrim_id", count="exact") \
            .gte("recorded_at", ten_min_ago) \
            .execute()
        # Distinct pilgrim count (approximate — Supabase free tier may not support distinct)
        online_pids = set()
        for r in (online_res.data or []):
            online_pids.add(r["pilgrim_id"])
        online_users = len(online_pids)

        active_sos = _safe_sos_count()

        return {
            "success": True,
            "data": {
                "total_agencies": total_agencies,
                "total_users": total_users,
                "online_users": online_users,
                "active_sos": active_sos,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agencies")
def get_agencies(user=Depends(require_admin)):
    """List all travel agencies with member counts."""
    try:
        res = supabase.table("agencies").select("*").execute()
        agencies = res.data or []

        # Enrich with user count per agency
        enriched = []
        for agency in agencies:
            try:
                count_res = supabase.table("users_table") \
                    .select("id", count="exact") \
                    .eq("agency_id", agency["id"]) \
                    .execute()
                agency["member_count"] = count_res.count or 0
            except Exception:
                agency["member_count"] = 0
            enriched.append(agency)

        return {"success": True, "data": enriched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agencies/{agency_id}/toggle")
def toggle_agency(agency_id: str, user=Depends(require_admin)):
    """Enable or disable a travel agency."""
    try:
        # Get current status
        res = supabase.table("agencies") \
            .select("status").eq("id", agency_id).limit(1).execute()
        if not res.data:
            return {"success": False, "error": "Agency not found"}
        current = res.data[0]["status"]
        new_status = "inactive" if current == "active" else "active"

        upd = supabase.table("agencies") \
            .update({"status": new_status}) \
            .eq("id", agency_id).execute()
        return {"success": True, "status": new_status}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/agencies/{agency_id}")
def delete_agency(agency_id: str, user=Depends(require_admin)):
    """
    Permanently delete a travel agency and all its associated data.
    WARNING: Also deletes all users (leaders/pilgrims) under this agency.
    """
    try:
        # Delete associated users first (cascade not guaranteed on all setups)
        supabase.table("users_table").delete().eq("agency_id", agency_id).execute()
        # Delete the agency
        res = supabase.table("agencies").delete().eq("id", agency_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Agency not found")
        return {"success": True, "message": f"Agency {agency_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
def delete_user(user_id: str, user=Depends(require_admin)):
    """Delete a user (leader or pilgrim) permanently."""
    try:
        res = supabase.table("users_table").delete().eq("id", user_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "message": f"User {user_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
def get_all_users(user=Depends(require_admin)):
    """List all users (leaders + pilgrims) for admin."""
    try:
        res = supabase.table("users_table") \
            .select("id, full_name, email, role, agency_id, leader_id, phone, journey_type, created_at") \
            .order("created_at", desc=True) \
            .limit(200) \
            .execute()
        users = res.data or []
        _attach_relations(users)
        return {"success": True, "data": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity")
def get_activity(user=Depends(require_admin)):
    """Return hourly activity from recorded locations and SOS alerts."""
    try:
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=23)

        loc_res = supabase.table("pilgrim_locations") \
            .select("pilgrim_id, recorded_at") \
            .gte("recorded_at", start.isoformat()) \
            .execute()
        sos_rows = _safe_sos_rows(start)

        buckets = []
        for offset in range(24):
            bucket_start = (start + timedelta(hours=offset)).replace(minute=0, second=0, microsecond=0)
            bucket_end = bucket_start + timedelta(hours=1)
            active_pilgrims = set()
            sos_count = 0

            for row in loc_res.data or []:
                recorded_at = _parse_dt(row.get("recorded_at"))
                if recorded_at and bucket_start <= recorded_at < bucket_end:
                    active_pilgrims.add(row.get("pilgrim_id"))

            for row in sos_rows:
                created_at = _parse_dt(row.get("created_at"))
                if created_at and bucket_start <= created_at < bucket_end:
                    sos_count += 1

            buckets.append({
                "time": bucket_start.isoformat(),
                "users": len(active_pilgrims),
                "sos": sos_count,
            })

        return {"success": True, "data": buckets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def get_system_health(user=Depends(require_admin)):
    """Return live API/database health for the admin dashboard."""
    started = time.perf_counter()
    try:
        supabase.table("agencies").select("id", count="exact").limit(1).execute()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "success": True,
            "data": [
                {
                    "component": "API Server",
                    "status": "Healthy",
                    "value": f"{elapsed_ms}ms database round trip",
                },
                {
                    "component": "Database",
                    "status": "Healthy",
                    "value": "Supabase reachable",
                },
            ],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "success": True,
            "data": [
                {
                    "component": "Database",
                    "status": "Error",
                    "value": f"{elapsed_ms}ms - {str(e)}",
                }
            ],
        }


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_missing_table_error(exc: Exception) -> bool:
    text = str(exc)
    return "PGRST205" in text or "schema cache" in text or "Could not find the table" in text


def _safe_sos_count() -> int:
    try:
        res = supabase.table("sos_alerts").select("id", count="exact").eq("status", "active").execute()
        return res.count or 0
    except Exception as e:
        if _is_missing_table_error(e):
            return 0
        raise


def _safe_sos_rows(start: datetime) -> list:
    try:
        res = supabase.table("sos_alerts").select("id, created_at").gte("created_at", start.isoformat()).execute()
        return res.data or []
    except Exception as e:
        if _is_missing_table_error(e):
            return []
        raise


def _attach_relations(users: list) -> None:
    agency_ids = {u.get("agency_id") for u in users if u.get("agency_id")}
    agency_names = {}
    for agency_id in agency_ids:
        try:
            res = supabase.table("agencies").select("name").eq("id", agency_id).limit(1).execute()
            agency_names[agency_id] = res.data[0].get("name") if res.data else None
        except Exception:
            agency_names[agency_id] = None

    leader_ids = {u.get("leader_id") for u in users if u.get("leader_id")}
    leader_names = {}
    for leader_id in leader_ids:
        try:
            res = supabase.table("users_table").select("full_name").eq("id", leader_id).limit(1).execute()
            leader_names[leader_id] = res.data[0].get("full_name") if res.data else None
        except Exception:
            leader_names[leader_id] = None

    for user in users:
        user["agency_name"] = agency_names.get(user.get("agency_id"))
        user["leader_name"] = leader_names.get(user.get("leader_id"))

from pydantic import EmailStr
import bcrypt

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "pilgrim"
    agency_id: str
    leader_id: str = None
    journey_type: str = None
    phone: str = None

@router.post("/users")
def create_user(body: CreateUserRequest, user=Depends(require_admin)):
    """Create a new user account (Admin only)."""
    try:
        # Hash password securely
        hashed_pw = bcrypt.hashpw(body.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        data = {
            "email": body.email.strip().lower(),
            "password_hash": hashed_pw,
            "full_name": body.full_name,
            "role": body.role,
            "agency_id": body.agency_id,
        }
        if body.leader_id:
            data["leader_id"] = body.leader_id
        if body.journey_type:
            data["journey_type"] = body.journey_type
        if body.phone:
            data["phone"] = body.phone
        res = supabase.table("users_table").insert(data).execute()
        if res.data:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from logger import log_event
            log_event(f"Created new {body.role}: {body.email}", user_id=user["sub"])
            return {"success": True, "user_id": res.data[0]["id"]}
            
        raise HTTPException(status_code=500, detail="Failed to create user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CreateAgencyRequest(BaseModel):
    name: str
    city: str
    status: str = "active"

@router.post("/agencies")
def create_agency(body: CreateAgencyRequest, user=Depends(require_admin)):
    try:
        data = {
            "name": body.name,
            "city": body.city,
            "status": body.status,
            "member_count": 0,
            "online_count": 0
        }
        res = supabase.table("agencies").insert(data).execute()
        if res.data:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from logger import log_event
            log_event(f"Admin created agency: {body.name}", user_id=user["sub"])
            return {"success": True, "data": res.data[0]}
        raise HTTPException(status_code=500, detail="Failed to create agency")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
def get_system_logs(user=Depends(require_admin)):
    try:
        res = supabase.table("system_logs").select("*").order("created_at", desc=True).limit(200).execute()
        return {"success": True, "data": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
