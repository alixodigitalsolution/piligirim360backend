from fastapi import APIRouter, Depends, HTTPException
from config import supabase
from auth.rbac import get_current_user

router = APIRouter()


@router.get("/offline-cache")
def get_offline_map_cache(user=Depends(get_current_user)):
    """Return database-managed map points for mobile offline caching and web map defaults."""
    try:
        points_res = (
            supabase.table("map_points")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        config_res = (
            supabase.table("app_settings")
            .select("setting_value")
            .eq("setting_key", "map_config")
            .limit(1)
            .execute()
        )
        config = config_res.data[0]["setting_value"] if config_res.data else {}
        return {
            "success": True,
            "map_cache": {
                "updated_at": config.get("updated_at"),
                "center": config.get("center"),
                "zoom": config.get("zoom", 14),
                "places": points_res.data or [],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
