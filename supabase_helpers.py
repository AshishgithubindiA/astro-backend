# supabase_helpers.py

from supabase import Client
from typing import Dict, List
import uuid
import datetime

def create_user(supabase: Client, user: dict):
    data = {
        "user_id": user['user_id'],
        "name": user.get('name'),
        "birth_data": {
            "year": user['birth_data']['year'],
            "month": user['birth_data']['month'],
            "day": user['birth_data']['day'],
            "hour": user['birth_data']['hour'],
            "minute": user['birth_data']['minute'],
            "timezone": user['birth_data']['timezone']
        }
    }
    try:
        response = supabase.table('users').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        raise Exception(f"Failed to create user: {str(e)}")

def get_user(supabase: Client, user_id: str):
    result = supabase.table('users').select("*").eq("user_id", user_id).single().execute()
    return result.data

def save_astro_profile(supabase: Client, user_id: str, profile: dict):
    data = {
        "user_id": user_id,
        "sun_sign": profile.get("sun_sign"),
        "moon_sign": profile.get("moon_sign"),
        "rising_sign": profile.get("rising_sign"),
        "natal_chart": profile.get("natal_chart")
    }
    return supabase.table('astro_profiles').upsert(data).execute()

def get_astro_profile(supabase: Client, user_id: str):
    result = supabase.table('astro_profiles').select("*").eq("user_id", user_id).single().execute()
    return result.data

def save_daily_context(supabase: Client, user_id: str, context: dict):
    data = {
        "user_id": user_id,
        "date": context["date"],
        "mood_score": context.get("mood_score"),
        "transits": context.get("transits"),
        "aspects_today": context.get("aspects_today"),
        "summary": context.get("summary")
    }
    return supabase.table('daily_context').upsert(data).execute()

def get_daily_context(supabase: Client, user_id: str, date: str):
    result = supabase.table('daily_context').select("*").eq("user_id", user_id).eq("date", date).single().execute()
    return result.data

def add_chat_message(supabase: Client, user_id: str, role: str, text: str):
    data = {
        "user_id": user_id,
        "role": role,
        "text": text
    }
    return supabase.table('chat_history').insert(data).execute()

def get_chat_history(supabase: Client, user_id: str, limit: int = 50, offset: int = 0):
    result = (
        supabase.table('chat_history')
        .select("*")
        .eq("user_id", user_id)
        .order("timestamp", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data

def save_preferences(supabase: Client, user_id: str, preferences: dict):
    data = {
        "user_id": user_id,
        "preferences": preferences
    }
    return supabase.table('preferences').upsert(data).execute()

def get_preferences(supabase: Client, user_id: str):
    result = supabase.table('preferences').select("*").eq("user_id", user_id).single().execute()
    return result.data

def log_mood_checkin(supabase: Client, user_id: str, mood_score: int, note: str = ""):
    data = {
        "user_id": user_id,
        "mood_score": mood_score,
        "note": note
    }
    return supabase.table('mood_logs').insert(data).execute()
