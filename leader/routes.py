# ============================================================
# leader/routes.py — Group Health Dashboard (Leader View)
# GET /leader/group-health     — All pilgrim status cards
# GET /leader/pilgrim/{id}     — Single pilgrim detail + location
# POST /notification/broadcast — Leader/Agency sends group message
# ============================================================
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
from datetime import datetime, timezone, timedelta

router = APIRouter()


def get_current_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def battery_color(level: Optional[int]) -> str:
    if level is None:
        return "gray"
    if level < 20:
        return "red"
    if level < 50:
        return "yellow"
    return "green"


def minutes_ago(timestamp_str: Optional[str]) -> Optional[int]:
    if not timestamp_str:
        return None
    try:
        cleaned = timestamp_str.replace("Z", "+00:00")
        ts = datetime.fromisoformat(cleaned)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - ts
        return int(diff.total_seconds() / 60)
    except Exception:
        return None


# ── Group Health Dashboard ─────────────────────────────────
@router.get("/group-health")
def get_group_health(
    group_id: str = Query(..., description="Group/Agency ID"),
    filter: Optional[str] = Query("all", description="all | offline | sos_active | low_battery"),
    authorization: str = Header(None),
):
    """
    Leader fetches all pilgrim status cards.
    Each card: online/offline, battery %, last ping, geofence, SOS indicator.
    """
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders can view group health")

    try:
        # Get all pilgrims in the group
        pilgrims_res = supabase.table("users_table") \
            .select("id, full_name, phone") \
            .eq("agency_id", group_id) \
            .eq("role", "pilgrim") \
            .execute()

        pilgrims = pilgrims_res.data or []
        cards = []
        now = datetime.now(timezone.utc)

        for pilgrim in pilgrims:
            pid = pilgrim["id"]

            # Latest location
            loc_res = supabase.table("pilgrim_locations") \
                .select("latitude, longitude, battery_level, is_online, recorded_at") \
                .eq("pilgrim_id", pid) \
                .order("recorded_at", desc=True) \
                .limit(1) \
                .execute()

            loc = loc_res.data[0] if loc_res.data else {}

            # Active SOS
            sos_res = supabase.table("sos_alerts") \
                .select("id, status") \
                .eq("pilgrim_id", pid) \
                .eq("status", "active") \
                .limit(1) \
                .execute()
            has_active_sos = bool(sos_res.data)

            # Latest check-in
            checkin_res = supabase.table("checkins") \
                .select("status, created_at") \
                .eq("user_id", pid) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            checkin = checkin_res.data[0] if checkin_res.data else {}

            battery = loc.get("battery_level")
            is_online = loc.get("is_online", False)
            last_ping_str = loc.get("recorded_at")
            mins = minutes_ago(last_ping_str)

            # Determine offline if no ping in 60 minutes
            if mins is not None and mins > 60:
                is_online = False

            last_ping_label = "Pata nahi"
            if mins is not None:
                if mins < 1:
                    last_ping_label = "Abhi abhi"
                elif mins < 60:
                    last_ping_label = f"{mins} minute pehle"
                elif mins < 1440:
                    last_ping_label = f"{mins // 60} ghante pehle"
                else:
                    last_ping_label = f"{mins // 1440} din pehle"

            card = {
                "user_id": pid,
                "full_name": pilgrim["full_name"],
                "phone": pilgrim.get("phone"),
                "is_online": is_online,
                "online_status_color": "green" if is_online else "red",
                "battery_level": battery,
                "battery_color": battery_color(battery),
                "last_ping": last_ping_str,
                "last_ping_label": last_ping_label,
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "has_active_sos": has_active_sos,
                "checkin_status": checkin.get("status"),
                "risk_score": (
                    100 if has_active_sos
                    else 80 if not is_online
                    else 60 if battery is not None and battery < 20
                    else 20
                ),
            }
            cards.append(card)

        # Apply filter
        if filter == "offline":
            cards = [c for c in cards if not c["is_online"]]
        elif filter == "sos_active":
            cards = [c for c in cards if c["has_active_sos"]]
        elif filter == "low_battery":
            cards = [c for c in cards if c.get("battery_level") is not None and c["battery_level"] < 20]

        # Sort by risk score (highest first)
        cards.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "success": True,
            "group_id": group_id,
            "total_pilgrims": len(pilgrims),
            "online_count": sum(1 for c in cards if c["is_online"]),
            "sos_active_count": sum(1 for c in cards if c["has_active_sos"]),
            "low_battery_count": sum(1 for c in cards if c.get("battery_level") is not None and c["battery_level"] < 20),
            "filter_applied": filter,
            "pilgrim_cards": cards,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Single Pilgrim Detail ──────────────────────────────────
@router.get("/pilgrim/{pilgrim_id}")
def get_pilgrim_detail(pilgrim_id: str, authorization: str = Header(None)):
    """Leader taps a pilgrim card to see full profile and location on map."""
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        user_res = supabase.table("users_table") \
            .select("id, full_name, phone, email") \
            .eq("id", pilgrim_id) \
            .limit(1).execute()

        if not user_res.data:
            raise HTTPException(status_code=404, detail="Pilgrim not found")

        pilgrim = user_res.data[0]

        loc_res = supabase.table("pilgrim_locations") \
            .select("*") \
            .eq("pilgrim_id", pilgrim_id) \
            .order("recorded_at", desc=True) \
            .limit(5).execute()

        medical_res = supabase.table("medical_cards") \
            .select("*") \
            .eq("user_id", pilgrim_id) \
            .limit(1).execute()

        sos_res = supabase.table("sos_alerts") \
            .select("*") \
            .eq("pilgrim_id", pilgrim_id) \
            .eq("status", "active") \
            .limit(1).execute()

        return {
            "success": True,
            "pilgrim": pilgrim,
            "location_history": loc_res.data,
            "medical_summary": medical_res.data[0] if medical_res.data else None,
            "active_sos": sos_res.data[0] if sos_res.data else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Broadcast Notification ─────────────────────────────────
class BroadcastRequest(BaseModel):
    group_id: str
    message: str
    message_type: Optional[str] = "text"  # text | alert | info
    priority: Optional[str] = "IMPORTANT"  # CRITICAL | IMPORTANT | INFO


@router.post("/broadcast")
def send_broadcast(body: BroadcastRequest, authorization: str = Header(None)):
    """Leader or Agency sends broadcast message to all pilgrims in a group."""
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders/admins can broadcast")

    try:
        # Save message to group_messages
        msg_data = {
            "group_id": body.group_id,
            "leader_id": user.get("sub"),
            "message_type": body.message_type,
            "message_text": body.message,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        msg_res = supabase.table("group_messages").insert(msg_data).execute()

        # Get all pilgrims in group and log notifications
        if user.get("role") == "leader":
            groups_res = supabase.table("pilgrim_groups").select("group_name").eq("leader_id", user["sub"]).execute()
            group_names = [g["group_name"] for g in (groups_res.data or [])]
            if group_names:
                pg_res = supabase.table("pilgrim_groups").select("pilgrim_id").in_("group_name", group_names).execute()
                pilgrim_ids = [p["pilgrim_id"] for p in (pg_res.data or []) if p.get("pilgrim_id")]
                if pilgrim_ids:
                    pilgrims_res = supabase.table("users_table") \
                        .select("id") \
                        .in_("id", pilgrim_ids) \
                        .execute()
                else:
                    pilgrims_res = type('obj', (object,), {'data': []})()
            else:
                pilgrims_res = type('obj', (object,), {'data': []})()
        else:
            pilgrims_res = supabase.table("users_table") \
                .select("id") \
                .eq("agency_id", body.group_id) \
                .eq("role", "pilgrim") \
                .execute()

        notif_rows = []
        for p in (pilgrims_res.data or []):
            notif_rows.append({
                "user_id": p["id"],
                "type": body.priority,
                "message": body.message,
                "delivered": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        if notif_rows:
            supabase.table("notifications_log").insert(notif_rows).execute()

        return {
            "success": True,
            "message": "Broadcast sent successfully",
            "recipients": len(notif_rows),
            "group_id": body.group_id,
            "message_id": msg_res.data[0]["id"] if msg_res.data else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import uuid
import bcrypt

class LeaderAddPilgrimRequest(BaseModel):
    group_name: str
    full_name: str
    phone: str
    email: Optional[str] = None
    password: Optional[str] = None
    journey_type: Optional[str] = "hajj"

def leader_hash_password(password: str) -> str:
    password = (password or "").strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    password_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")

@router.get("/my-groups")
def get_my_groups(authorization: str = Header(None)):
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders/admins can view group info")
    
    try:
        # Fetch group names assigned to this leader
        groups_res = supabase.table("pilgrim_groups") \
            .select("group_name, group_code, agency_id") \
            .eq("leader_id", user["sub"]) \
            .execute()
        
        if not groups_res.data:
            return {"success": True, "groups": [], "group_names": [], "groups_list": []}
            
        group_names = list(set([r["group_name"] for r in groups_res.data]))
        agency_id = groups_res.data[0]["agency_id"]
        
        # Build unique list of groups with their code
        groups_list = []
        seen = set()
        for r in groups_res.data:
            gname = r["group_name"]
            if gname not in seen:
                seen.add(gname)
                gcode = r.get("group_code")
                if not gcode:
                    import hashlib
                    gcode = hashlib.md5(f"{gname}{agency_id}".encode()).hexdigest()[:6].upper()
                groups_list.append({"id": gcode, "group_name": gname})
        
        # Fetch all pilgrim IDs in these groups
        pg_res = supabase.table("pilgrim_groups") \
            .select("group_name, pilgrim_id") \
            .in_("group_name", group_names) \
            .execute()
            
        pilgrim_ids = [p["pilgrim_id"] for p in (pg_res.data or []) if p.get("pilgrim_id")]
        
        pilgrims = []
        if pilgrim_ids:
            # Fetch user profiles
            u_res = supabase.table("users_table") \
                .select("id, full_name, email, phone, journey_type") \
                .in_("id", pilgrim_ids) \
                .execute()
            
            p_group_map = {p["pilgrim_id"]: p["group_name"] for p in pg_res.data}
            for u in (u_res.data or []):
                u["group_name"] = p_group_map.get(u["id"])
                pilgrims.append(u)
                
        return {
            "success": True,
            "group_names": group_names,
            "groups_list": groups_list,
            "pilgrims": pilgrims,
            "agency_id": agency_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pilgrims")
def leader_add_pilgrim(body: LeaderAddPilgrimRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders/admins can add pilgrims")
        
    try:
        # Get leader's agency_id
        agency_res = supabase.table("users_table").select("agency_id").eq("id", user["sub"]).limit(1).execute()
        if not agency_res.data or not agency_res.data[0].get("agency_id"):
            raise HTTPException(status_code=400, detail="Leader has no agency assigned")
        agency_id = agency_res.data[0]["agency_id"]
        
        # Verify leader is assigned to the group (if user is leader)
        if user.get("role") == "leader":
            check_group = supabase.table("pilgrim_groups") \
                .select("id") \
                .eq("leader_id", user["sub"]) \
                .eq("group_name", body.group_name) \
                .limit(1) \
                .execute()
            if not check_group.data:
                raise HTTPException(status_code=403, detail="You are not assigned to this group")
                
        email = body.email or f"{body.phone}@pilgrim360.app"
        
        # Check duplicate email
        existing = supabase.table("users_table").select("id").eq("email", email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="A pilgrim with this phone/email already exists")
            
        initial_password = body.password or body.phone
        hashed_pw = leader_hash_password(initial_password)
        
        pilgrim_id = str(uuid.uuid4())
        new_pilgrim = {
            "id": pilgrim_id,
            "email": email,
            "password_hash": hashed_pw,
            "full_name": body.full_name,
            "role": "pilgrim",
            "agency_id": agency_id,
            "leader_id": user["sub"],
            "phone": body.phone,
            "journey_type": body.journey_type,
        }
        
        # Insert pilgrim user
        supabase.table("users_table").insert(new_pilgrim).execute()
        
        # Get existing group code
        gcode_res = supabase.table("pilgrim_groups") \
            .select("group_code") \
            .eq("agency_id", agency_id) \
            .eq("group_name", body.group_name) \
            .limit(1) \
            .execute()
            
        gcode = None
        if gcode_res.data and gcode_res.data[0].get("group_code"):
            gcode = gcode_res.data[0]["group_code"]
        else:
            import hashlib
            gcode = hashlib.md5(f"{body.group_name}{agency_id}".encode()).hexdigest()[:6].upper()

        # Insert group assignment
        supabase.table("pilgrim_groups").insert({
            "group_name": body.group_name,
            "agency_id": agency_id,
            "leader_id": user["sub"],
            "pilgrim_id": pilgrim_id,
            "group_code": gcode
        }).execute()
        
        # Create empty medical card
        supabase.table("medical_cards").insert({
            "user_id": pilgrim_id,
            "blood_type": "O+",
            "allergies": "",
            "medications": "",
            "medical_history": "",
            "emergency_contact_name": "",
            "emergency_contact_phone": "",
        }).execute()
        
        return {
            "success": True,
            "message": f"Pilgrim '{body.full_name}' added successfully",
            "pilgrim": {
                "id": pilgrim_id,
                "full_name": body.full_name,
                "phone": body.phone,
                "group_name": body.group_name
            }
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/pilgrims/{pilgrim_id}")
def leader_delete_pilgrim(pilgrim_id: str, authorization: str = Header(None)):
    user = get_current_user(authorization)
    if user.get("role") not in ["leader", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only leaders/admins can delete pilgrims")
        
    try:
        # Get pilgrim info
        p_res = supabase.table("users_table").select("full_name, agency_id").eq("id", pilgrim_id).eq("role", "pilgrim").limit(1).execute()
        if not p_res.data:
            raise HTTPException(status_code=404, detail="Pilgrim not found")
        full_name = p_res.data[0]["full_name"]
        
        # If leader, ensure pilgrim is in one of the leader's groups
        if user.get("role") == "leader":
            groups_res = supabase.table("pilgrim_groups").select("group_name").eq("leader_id", user["sub"]).execute()
            group_names = [g["group_name"] for g in (groups_res.data or [])]
            if not group_names:
                raise HTTPException(status_code=403, detail="You do not have any groups assigned")
                
            check_p = supabase.table("pilgrim_groups") \
                .select("id") \
                .in_("group_name", group_names) \
                .eq("pilgrim_id", pilgrim_id) \
                .limit(1) \
                .execute()
            if not check_p.data:
                raise HTTPException(status_code=403, detail="This pilgrim does not belong to any of your groups")
                
        # Perform deletion
        supabase.table("users_table").delete().eq("id", pilgrim_id).execute()
        return {"success": True, "message": f"Pilgrim '{full_name}' removed successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
