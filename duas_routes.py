from fastapi import APIRouter, HTTPException, Query
from config import supabase

router = APIRouter()


@router.get("/catalog")
def get_duas_catalog(journey_type: str = Query("umrah")):
    """Return duas grouped by category from Supabase."""
    try:
        allowed = [journey_type, "both"]
        cats_res = (
            supabase.table("dua_categories")
            .select("*")
            .in_("journey_type", allowed)
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        categories = cats_res.data or []
        for category in categories:
            duas_res = (
                supabase.table("duas")
                .select("*")
                .eq("category_id", category["id"])
                .eq("is_active", True)
                .order("sort_order")
                .execute()
            )
            category["duas"] = duas_res.data or []
        return {"success": True, "categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasbeehat")
def get_tasbeehat():
    """Return smart tasbeeh entries from Supabase."""
    try:
        res = (
            supabase.table("tasbeehat")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        return {"success": True, "tasbeehat": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
