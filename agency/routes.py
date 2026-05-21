# ============================================================
# agency/routes.py — Agency & Group Leader Management
# POST   /agency/leaders          — Add new group leader
# DELETE /agency/leaders/{id}     — Remove group leader
# GET    /agency/leaders          — List all leaders
# POST   /agency/pilgrims         — Add pilgrim to agency
# DELETE /agency/pilgrims/{id}    — Remove pilgrim
# GET    /agency/pilgrims         — List all pilgrims
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
from passlib.context import CryptContext
import uuid

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_current_user(authorization: str):
    """Extract and validate JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_user_agency_id(user: dict) -> str:
    """Resolve the authenticated user's agency scope."""
    agency_id = user.get("agency_id")
    if agency_id:
        return agency_id

    res = supabase.table("users_table") \
        .select("agency_id") \
        .eq("id", user.get("sub")) \
        .limit(1) \
        .execute()

    agency_id = res.data[0].get("agency_id") if res.data else None
    if not agency_id:
        raise HTTPException(status_code=400, detail="No agency assigned to this account")
    return agency_id


# ── Models ─────────────────────────────────────────────────
class AddLeaderRequest(BaseModel):
    email: str
    full_name: str
    phone: Optional[str] = None
    password: str = "Leader@123"  # Default password, leader changes on first login


class UpdateLeaderRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


class AddPilgrimRequest(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    password: Optional[str] = None
    leader_id: Optional[str] = None


def hash_bcrypt_password(password: str) -> str:
    """Hash with bcrypt's 72-byte input limit handled explicitly using standard bcrypt."""
    password = (password or "").strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    import bcrypt
    password_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def ensure_leader_in_agency(leader_id: Optional[str], agency_id: str):
    if not leader_id:
        return
    leader_res = supabase.table("users_table") \
        .select("id") \
        .eq("id", leader_id) \
        .eq("role", "leader") \
        .eq("agency_id", agency_id) \
        .limit(1) \
        .execute()
    if not leader_res.data:
        raise HTTPException(status_code=400, detail="Selected leader does not belong to this agency")


# ── Leader Endpoints ───────────────────────────────────────
@router.post("/leaders")
def add_leader(body: AddLeaderRequest, authorization: str = Header(None)):
    """Agency adds a new group leader under their agency."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only agency admins can add leaders")

    agency_id = get_user_agency_id(user)

    # Check if email already exists
    existing = supabase.table("users_table").select("id").eq("email", body.email.lower()).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_bcrypt_password(body.password)
    new_leader = {
        "id": str(uuid.uuid4()),
        "email": body.email.strip().lower(),
        "password_hash": hashed_pw,
        "full_name": body.full_name,
        "role": "leader",
        "agency_id": agency_id,
        "phone": body.phone,
    }
    try:
        res = supabase.table("users_table").insert(new_leader).execute()
        if res.data:
            leader = res.data[0]
            return {
                "success": True,
                "message": f"Group leader '{body.full_name}' added successfully",
                "leader": {
                    "id": leader["id"],
                    "full_name": leader["full_name"],
                    "email": leader["email"],
                    "phone": leader.get("phone"),
                    "role": "leader",
                    "agency_id": agency_id,
                }
            }
        raise HTTPException(status_code=500, detail="Failed to add leader")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/leaders/{leader_id}")
def update_leader(leader_id: str, body: UpdateLeaderRequest, authorization: str = Header(None)):
    """Agency edits a group leader in their agency."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only agency admins can edit leaders")

    agency_id = get_user_agency_id(user)
    check = supabase.table("users_table") \
        .select("id, agency_id") \
        .eq("id", leader_id) \
        .eq("role", "leader") \
        .limit(1) \
        .execute()

    if not check.data:
        raise HTTPException(status_code=404, detail="Leader not found")
    if check.data[0]["agency_id"] != agency_id and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="This leader does not belong to your agency")

    update_data = {}
    if body.full_name is not None:
        update_data["full_name"] = body.full_name.strip()
    if body.email is not None:
        email = body.email.strip().lower()
        existing = supabase.table("users_table").select("id").eq("email", email).neq("id", leader_id).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        update_data["email"] = email
    if body.phone is not None:
        update_data["phone"] = body.phone.strip() or None
    if body.password:
        update_data["password_hash"] = hash_bcrypt_password(body.password)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        res = supabase.table("users_table").update(update_data).eq("id", leader_id).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to update leader")
        return {"success": True, "leader": res.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/leaders/{leader_id}")
def delete_leader(leader_id: str, authorization: str = Header(None)):
    """Agency removes a group leader."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only agency admins can delete leaders")

    agency_id = get_user_agency_id(user)

    # Verify leader belongs to this agency
    check = supabase.table("users_table") \
        .select("id, full_name, agency_id") \
        .eq("id", leader_id) \
        .eq("role", "leader") \
        .execute()

    if not check.data:
        raise HTTPException(status_code=404, detail="Leader not found")

    leader = check.data[0]
    if leader["agency_id"] != agency_id and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="This leader does not belong to your agency")

    try:
        supabase.table("users_table").delete().eq("id", leader_id).execute()
        return {"success": True, "message": f"Leader '{leader['full_name']}' removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaders")
def list_leaders(authorization: str = Header(None)):
    """List all group leaders under the agency, including dynamic stats."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin", "leader", "pilgrim"]:
        raise HTTPException(status_code=403, detail="Not authorized to view leaders")

    agency_id = get_user_agency_id(user)

    try:
        query = supabase.table("users_table") \
            .select("id, full_name, email, phone, created_at") \
            .eq("role", "leader")

        # Super admin sees all; agency users see only theirs
        if user.get("role") != "super_admin":
            query = query.eq("agency_id", agency_id)

        res = query.execute()
        leaders = res.data or []

        # Fetch all pilgrim_groups for this agency to calculate stats
        pg_res = supabase.table("pilgrim_groups") \
            .select("group_name, leader_id, pilgrim_id") \
            .eq("agency_id", agency_id) \
            .execute()

        # Map group name -> list of leader ids and pilgrim ids
        group_leaders = {}
        group_pilgrims = {}

        for row in (pg_res.data or []):
            gname = row["group_name"]
            lid = row.get("leader_id")
            pid = row.get("pilgrim_id")

            if gname not in group_leaders:
                group_leaders[gname] = set()
            if gname not in group_pilgrims:
                group_pilgrims[gname] = set()

            if lid:
                group_leaders[gname].add(lid)
            if pid:
                group_pilgrims[gname].add(pid)

        # Calculate counts
        for leader in leaders:
            lid = leader["id"]
            # Find groups led by this leader
            assigned_groups = [gname for gname, lids in group_leaders.items() if lid in lids]
            
            # Count unique pilgrims in those groups
            pilgrims_set = set()
            for gname in assigned_groups:
                pilgrims_set.update(group_pilgrims[gname])

            leader["group_count"] = len(assigned_groups)
            leader["pilgrim_count"] = len(pilgrims_set)

        return {"success": True, "leaders": leaders, "count": len(leaders)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Pilgrim Endpoints ──────────────────────────────────────
@router.post("/pilgrims")
def add_pilgrim(body: AddPilgrimRequest, authorization: str = Header(None)):
    """Agency adds a new pilgrim account."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin", "leader"]:
        raise HTTPException(status_code=403, detail="Not authorized to add pilgrims")

    agency_id = get_user_agency_id(user)

    # Generate unique email if not provided (phone-based)
    email = body.email or f"{body.phone}@pilgrim360.app"

    # Check duplicate
    existing = supabase.table("users_table").select("id").eq("email", email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Pilgrim with this phone/email already exists")

    ensure_leader_in_agency(body.leader_id, agency_id)

    initial_password = body.password or body.phone
    hashed_pw = hash_bcrypt_password(initial_password)
    new_pilgrim = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hashed_pw,
        "full_name": body.full_name,
        "role": "pilgrim",
        "agency_id": agency_id,
        "leader_id": body.leader_id,
        "phone": body.phone,
        "journey_type": None,
    }
    try:
        res = supabase.table("users_table").insert(new_pilgrim).execute()
        if res.data:
            pilgrim = res.data[0]
            return {
                "success": True,
                "message": f"Pilgrim '{body.full_name}' added successfully",
                "pilgrim": {
                    "id": pilgrim["id"],
                    "full_name": pilgrim["full_name"],
                    "phone": pilgrim.get("phone"),
                    "role": "pilgrim",
                    "leader_id": pilgrim.get("leader_id"),
                    "journey_type": pilgrim.get("journey_type"),
                }
            }
        raise HTTPException(status_code=500, detail="Failed to add pilgrim")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pilgrims/{pilgrim_id}")
def delete_pilgrim(pilgrim_id: str, authorization: str = Header(None)):
    """Agency removes a pilgrim account."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin", "leader"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete pilgrims")

    agency_id = get_user_agency_id(user)
    check = supabase.table("users_table") \
        .select("id, full_name, agency_id") \
        .eq("id", pilgrim_id) \
        .eq("role", "pilgrim") \
        .execute()

    if not check.data:
        raise HTTPException(status_code=404, detail="Pilgrim not found")
    if check.data[0]["agency_id"] != agency_id and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="This pilgrim does not belong to your agency")

    supabase.table("users_table").delete().eq("id", pilgrim_id).execute()
    return {"success": True, "message": f"Pilgrim '{check.data[0]['full_name']}' removed successfully"}


@router.get("/pilgrims")
def list_pilgrims(authorization: str = Header(None)):
    """List all pilgrims under the agency."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin", "leader"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    agency_id = get_user_agency_id(user)

    try:
        query = supabase.table("users_table") \
            .select("id, full_name, phone, email, leader_id, journey_type, created_at") \
            .eq("role", "pilgrim")

        if user.get("role") != "super_admin":
            query = query.eq("agency_id", agency_id)

        res = query.execute()
        return {"success": True, "pilgrims": res.data, "count": len(res.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Group Models ───────────────────────────────────────────
class GroupSaveRequest(BaseModel):
    group_name: str
    leader_ids: list[str] = []
    pilgrim_ids: list[str] = []
    group_code: str = None


# ── Group Endpoints ────────────────────────────────────────
@router.get("/groups")
def list_groups(authorization: str = Header(None)):
    """List all pilgrim groups under the agency."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to view groups")

    agency_id = get_user_agency_id(user)

    try:
        # Fetch all agency users (leaders and pilgrims) to map names/details
        users_res = supabase.table("users_table") \
            .select("id, full_name, email, phone, role") \
            .eq("agency_id", agency_id) \
            .execute()
        
        user_map = {u["id"]: u for u in users_res.data}

        # Fetch all group assignments
        groups_res = supabase.table("pilgrim_groups") \
            .select("id, group_name, leader_id, pilgrim_id, group_code") \
            .eq("agency_id", agency_id) \
            .execute()

        # Group them in python
        groups_dict = {}
        for row in groups_res.data:
            gname = row["group_name"]
            if gname not in groups_dict:
                gcode = row.get("group_code")
                if not gcode:
                    import hashlib
                    gcode = hashlib.md5(f"{gname}{agency_id}".encode()).hexdigest()[:6].upper()
                groups_dict[gname] = {
                    "group_name": gname,
                    "group_code": gcode,
                    "leaders": [],
                    "pilgrims": []
                }
            
            # Map leader
            leader_id = row.get("leader_id")
            if leader_id and leader_id in user_map:
                if not any(l["id"] == leader_id for l in groups_dict[gname]["leaders"]):
                    groups_dict[gname]["leaders"].append({
                        "id": leader_id,
                        "full_name": user_map[leader_id]["full_name"],
                        "email": user_map[leader_id]["email"],
                        "phone": user_map[leader_id].get("phone")
                    })
            
            # Map pilgrim
            pilgrim_id = row.get("pilgrim_id")
            if pilgrim_id and pilgrim_id in user_map:
                if not any(p["id"] == pilgrim_id for p in groups_dict[gname]["pilgrims"]):
                    groups_dict[gname]["pilgrims"].append({
                        "id": pilgrim_id,
                        "full_name": user_map[pilgrim_id]["full_name"],
                        "email": user_map[pilgrim_id]["email"],
                        "phone": user_map[pilgrim_id].get("phone")
                    })

        return {"success": True, "groups": list(groups_dict.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/groups")
def save_group(body: GroupSaveRequest, authorization: str = Header(None)):
    """Create or update a pilgrim group. Assigns multiple leaders and multiple pilgrims."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to manage groups")

    agency_id = get_user_agency_id(user)
    gname = body.group_name.strip()
    if not gname:
        raise HTTPException(status_code=400, detail="Group name cannot be empty")

    try:
        # Check if the group already exists to keep its code, otherwise generate a new one
        existing = supabase.table("pilgrim_groups") \
            .select("group_code") \
            .eq("agency_id", agency_id) \
            .eq("group_name", gname) \
            .limit(1) \
            .execute()
            
        gcode = None
        if body.group_code and body.group_code.strip():
            gcode = body.group_code.strip()
            # Validate global uniqueness of custom code
            dup_res = supabase.table("pilgrim_groups") \
                .select("group_name") \
                .eq("group_code", gcode) \
                .neq("group_name", gname) \
                .limit(1) \
                .execute()
            if dup_res.data:
                raise HTTPException(
                    status_code=400,
                    detail=f"The group code '{gcode}' is already in use by another group."
                )
        elif existing.data and existing.data[0].get("group_code"):
            gcode = existing.data[0]["group_code"]
        else:
            import random
            import string
            # Generate a globally unique code
            while True:
                gcode = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                dup_res = supabase.table("pilgrim_groups") \
                    .select("group_name") \
                    .eq("group_code", gcode) \
                    .limit(1) \
                    .execute()
                if not dup_res.data:
                    break

        # 1. Clean up existing assignments for this group name
        supabase.table("pilgrim_groups") \
            .delete() \
            .eq("agency_id", agency_id) \
            .eq("group_name", gname) \
            .execute()

        # 2. Remove selected pilgrims from any other groups to avoid uniqueness constraint violation
        if body.pilgrim_ids:
            supabase.table("pilgrim_groups") \
                .delete() \
                .eq("agency_id", agency_id) \
                .in_("pilgrim_id", body.pilgrim_ids) \
                .execute()

        # 3. Create new rows
        rows = []
        for lid in body.leader_ids:
            rows.append({
                "group_name": gname,
                "agency_id": agency_id,
                "leader_id": lid,
                "pilgrim_id": None,
                "group_code": gcode
            })

        for pid in body.pilgrim_ids:
            rows.append({
                "group_name": gname,
                "agency_id": agency_id,
                "leader_id": primary_leader,
                "pilgrim_id": pid,
                "group_code": gcode
            })

        if not rows:
            rows.append({
                "group_name": gname,
                "agency_id": agency_id,
                "leader_id": None,
                "pilgrim_id": None,
                "group_code": gcode
            })

        res = supabase.table("pilgrim_groups").insert(rows).execute()
        
        # 4. Sync users_table.leader_id for all pilgrims in this group
        # This keeps compatibility with the mobile app / existing views!
        primary_leader = body.leader_ids[0] if body.leader_ids else None
        if body.pilgrim_ids:
            for pid in body.pilgrim_ids:
                supabase.table("users_table") \
                    .update({"leader_id": primary_leader}) \
                    .eq("id", pid) \
                    .execute()

        return {"success": True, "message": f"Group '{gname}' saved successfully", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/groups/{group_name}")
def delete_group(group_name: str, authorization: str = Header(None)):
    """Delete a pilgrim group entirely (removing assignments)."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete groups")

    agency_id = get_user_agency_id(user)

    try:
        # Find pilgrims currently in this group
        pilgrims_res = supabase.table("pilgrim_groups") \
            .select("pilgrim_id") \
            .eq("agency_id", agency_id) \
            .eq("group_name", group_name) \
            .execute()

        pids = [r["pilgrim_id"] for r in pilgrims_res.data if r.get("pilgrim_id")]

        # Reset their leader_id in users_table
        if pids:
            supabase.table("users_table") \
                .update({"leader_id": None}) \
                .in_("id", pids) \
                .execute()

        # Delete group entries
        supabase.table("pilgrim_groups") \
            .delete() \
            .eq("agency_id", agency_id) \
            .eq("group_name", group_name) \
            .execute()

        return {"success": True, "message": f"Group '{group_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unassigned-pilgrims")
def list_unassigned_pilgrims(authorization: str = Header(None)):
    """List all pilgrims who are not currently assigned to any group."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    agency_id = get_user_agency_id(user)

    try:
        # Fetch all pilgrims of the agency
        all_pilgrims = supabase.table("users_table") \
            .select("id, full_name, email, phone") \
            .eq("role", "pilgrim") \
            .eq("agency_id", agency_id) \
            .execute()

        # Fetch all assigned pilgrim IDs
        assigned = supabase.table("pilgrim_groups") \
            .select("pilgrim_id") \
            .eq("agency_id", agency_id) \
            .execute()

        assigned_ids = {r["pilgrim_id"] for r in assigned.data if r.get("pilgrim_id")}

        unassigned = [p for p in all_pilgrims.data if p["id"] not in assigned_ids]

        return {"success": True, "pilgrims": unassigned, "count": len(unassigned)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-group-code")
def check_group_code(code: str, exclude_group_name: Optional[str] = None, authorization: str = Header(None)):
    """Check if a group code is available (not used by other groups)."""
    user = get_current_user(authorization)
    if user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    code = code.strip()
    if not code:
        return {"available": True}

    try:
        query = supabase.table("pilgrim_groups").select("group_name").eq("group_code", code)
        if exclude_group_name:
            query = query.neq("group_name", exclude_group_name)

        res = query.limit(1).execute()
        return {"available": len(res.data) == 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
