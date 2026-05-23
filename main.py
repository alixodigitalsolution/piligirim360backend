# ============================================================
# main.py — Pilgrim360 FastAPI Backend v2.0
# Run: uvicorn main:app --reload --port 8001
# Docs: http://localhost:8001/docs
# ============================================================
import platform
platform.system = lambda: "Windows"
platform.release = lambda: "10"
platform.python_version = lambda: "3.12.0"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Existing Routers ───────────────────────────────────────
from auth.login import router as auth_router
from location.routes import router as location_router
from messaging.routes import router as messaging_router
from admin.routes import router as admin_router
from emergency.routes import router as emergency_router
from medical.routes import router as medical_router
from sync.routes import router as sync_router
from tracking.routes import router as tracking_router

# ── New Routers (v2.0 — Document Section 9) ───────────────
from agency.routes import router as agency_router
from meeting_point.routes import router as meeting_point_router
from hotel.routes import router as hotel_router
from health.routes import router as health_router
from family.routes import router as family_router
from slots.routes import router as slots_router
from leader.routes import router as leader_router
from diary.routes import router as diary_router
from medicine.routes import router as medicine_router
from map_routes import router as map_router
from duas_routes import router as duas_router
from pilgrim_routes import router as pilgrim_router

app = FastAPI(
    title="Pilgrim360 API",
    description="B2B SaaS Backend for Hajj & Umrah Tour Operators. Supports Super Admin, Agency, Group Leader, and Pilgrim roles.",
    version="2.0.0",
)

# ── CORS — allow React dev server ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from logger import log_event

@app.middleware("http")
async def log_requests(request: Request, call_next):
    path = request.url.path
    method = request.method
    try:
        response = await call_next(request)
        if method != "OPTIONS" and path not in ["/health", "/docs", "/openapi.json"]:
            # Basic request log
            log_event(f"{method} {path} - {response.status_code}")
        return response
    except Exception as e:
        log_event(f"Error on {method} {path}: {str(e)}", level="error")
        raise

# ── Existing Routers ───────────────────────────────────────
app.include_router(auth_router,           prefix="/auth",        tags=["Auth"])
app.include_router(location_router,       prefix="/location",    tags=["Location"])
app.include_router(messaging_router,      prefix="/messaging",   tags=["Messaging"])
app.include_router(admin_router,          prefix="/admin",       tags=["Admin"])
app.include_router(emergency_router,      prefix="/emergency",   tags=["Emergency"])
app.include_router(medical_router,        prefix="/medical",     tags=["Medical"])
app.include_router(sync_router,           prefix="/sync",        tags=["Sync"])
app.include_router(tracking_router,       prefix="/tracking",    tags=["Tracking"])

# ── New Routers v2.0 ───────────────────────────────────────
app.include_router(agency_router,         prefix="/agency",      tags=["Agency Management"])
app.include_router(meeting_point_router,  prefix="/group",       tags=["Meeting Point"])
app.include_router(slots_router,          prefix="/group/slots", tags=["Jamarat Slots"])
app.include_router(hotel_router,          prefix="/hotel",       tags=["Hotel & Transport"])
app.include_router(health_router,         prefix="/health",      tags=["Health & Temperature"])
app.include_router(family_router,         prefix="/family",      tags=["Family Tracking"])
app.include_router(leader_router,         prefix="/leader",      tags=["Leader Dashboard"])
app.include_router(diary_router,          prefix="/diary",       tags=["Hajj/Umrah Diary"])
app.include_router(medicine_router,       prefix="/medicine",    tags=["Medicine Reminders"])
app.include_router(map_router,            prefix="/map",         tags=["Offline Map"])
app.include_router(duas_router,           prefix="/duas",        tags=["Duas"])
app.include_router(pilgrim_router,        prefix="/pilgrim",     tags=["Pilgrim"])


@app.get("/", tags=["Health"])
def root():
    return {
        "app": "Pilgrim360 API",
        "version": "2.0.0",
        "status": "🟢 Running",
        "docs": "/docs",
        "total_modules": 17,
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
