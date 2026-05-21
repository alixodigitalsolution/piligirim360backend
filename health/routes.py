# ============================================================
# health/routes.py — Heatstroke Warning + Pilgrim Check-In
# GET  /health/temperature       — Live Makkah/Madinah temperature
# POST /pilgrim/checkin          — Pilgrim confirms they are okay
# GET  /pilgrim/checkin/{user_id}— Get latest check-in status
# ============================================================
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError
from config import supabase, JWT_SECRET, JWT_ALGORITHM
from datetime import datetime, timezone
import httpx

router = APIRouter()

# Makkah coordinates
MAKKAH_LAT = 21.3891
MAKKAH_LNG = 39.8579
MADINAH_LAT = 24.5247
MADINAH_LNG = 39.5692

HEATSTROKE_THRESHOLD = 42.0  # Celsius


def get_current_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def fetch_temperature(lat: float, lng: float) -> dict:
    """Fetch live temperature from Open-Meteo API (free, no API key)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}"
        f"&current_weather=true"
        f"&hourly=temperature_2m,relative_humidity_2m,apparent_temperature"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current_weather", {})
        return {
            "temperature_celsius": current.get("temperature"),
            "wind_speed_kmh": current.get("windspeed"),
            "weather_code": current.get("weathercode"),
            "is_day": bool(current.get("is_day", 1)),
        }


# ── Temperature Endpoint ───────────────────────────────────
@router.get("/temperature")
async def get_temperature(city: str = "makkah"):
    """
    Fetch live temperature for Makkah or Madinah.
    Returns heatstroke warning if temp >= 42°C.
    No API key required (Open-Meteo is free).
    """
    city = city.lower()
    if city == "madinah":
        lat, lng = MADINAH_LAT, MADINAH_LNG
        city_name = "Madinah"
    else:
        lat, lng = MAKKAH_LAT, MAKKAH_LNG
        city_name = "Makkah"

    try:
        temp_data = await fetch_temperature(lat, lng)
        temp = temp_data.get("temperature_celsius", 0)

        heatstroke_warning = temp is not None and temp >= HEATSTROKE_THRESHOLD
        warning_message = None
        if heatstroke_warning:
            warning_message = (
                f"⚠️ {city_name} mein garmi bohat zyada hai ({temp}°C). "
                "Pani piyen, chhaon mein jayen, bahar nikalne se ghurez karen."
            )

        return {
            "success": True,
            "city": city_name,
            "temperature_celsius": temp,
            "wind_speed_kmh": temp_data.get("wind_speed_kmh"),
            "heatstroke_warning": heatstroke_warning,
            "warning_message": warning_message,
            "threshold_celsius": HEATSTROKE_THRESHOLD,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.RequestError:
        # Return fallback if network unavailable
        return {
            "success": False,
            "city": city_name,
            "temperature_celsius": None,
            "heatstroke_warning": False,
            "warning_message": "Temperature data unavailable — check manually",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Check-In Models ────────────────────────────────────────
class CheckInRequest(BaseModel):
    status: str               # "ok" | "not_ok"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    note: Optional[str] = None


# ── Check-In Endpoint ──────────────────────────────────────
@router.post("/checkin")
def pilgrim_checkin(body: CheckInRequest, authorization: str = Header(None)):
    """
    Pilgrim confirms they are okay (or not).
    If 'not_ok', group leader gets an alert with pilgrim location.
    """
    user = get_current_user(authorization)
    user_id = user.get("sub")

    if body.status not in ["ok", "not_ok"]:
        raise HTTPException(status_code=400, detail="Status must be 'ok' or 'not_ok'")

    checkin_data = {
        "user_id": user_id,
        "status": body.status,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "note": body.note,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        res = supabase.table("checkins").insert(checkin_data).execute()

        response = {
            "success": True,
            "message": "Check-in recorded",
            "status": body.status,
            "checkin_id": res.data[0].get("id") if res.data else None,
        }

        # If not_ok, create an alert for leader
        if body.status == "not_ok":
            # Get user info for alert
            user_info = supabase.table("users_table") \
                .select("full_name, agency_id") \
                .eq("id", user_id) \
                .execute()

            if user_info.data:
                pilgrim_name = user_info.data[0].get("full_name", "Unknown Pilgrim")
                alert = {
                    "user_id": user_id,
                    "type": "HEALTH_ALERT",
                    "message": f"🚨 {pilgrim_name} ne bataya hai ke woh theek nahi hain. Unka location check karen.",
                    "delivered": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                supabase.table("notifications_log").insert(alert).execute()

            response["leader_alerted"] = True
            response["alert_message"] = "Aapke leader ko alert bhej diya gaya hai"

        return response
    except Exception as e:
        return {
            "success": False,
            "message": "Check-in could not be saved, but the app received your response.",
            "status": body.status,
            "detail": str(e),
        }


@router.get("/checkin/{user_id}")
def get_checkin_status(user_id: str, authorization: str = Header(None)):
    """Get latest check-in status for a pilgrim."""
    get_current_user(authorization)

    try:
        res = supabase.table("checkins") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if not res.data:
            return {"success": True, "checkin": None, "message": "No check-in recorded"}
        return {"success": True, "checkin": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
