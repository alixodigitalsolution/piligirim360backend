# backend/logger.py
"""Simple logger utility to record system events in Supabase.

Usage:
    from logger import log_event
    log_event(message: str, user_id: Optional[str] = None)

The function inserts a row into the `system_logs` table with fields:
    - action (text)
    - level (text) defaults to 'info'
    - user_id (optional UUID/string)
    - created_at (timestamp, defaults to now on the DB side)
"""
import os
from typing import Optional
from config import supabase

def log_event(message: str, level: str = "info", user_id: Optional[str] = None) -> bool:
    """Insert a log entry into the `system_logs` table.
    Returns True on success, False otherwise.
    """
    try:
        payload = {
            "action": message,
            "level": level,
        }
        if user_id:
            payload["user_id"] = user_id
        # Assuming Supabase table `system_logs` exists with appropriate columns
        res = supabase.table("system_logs").insert(payload).execute()
        return bool(res.data)
    except Exception as e:
        # In production you might fallback to file logging
        print(f"[LOGGER ERROR] {e}")
        return False
