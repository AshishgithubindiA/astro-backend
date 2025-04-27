# Swiss Ephemeris Astrology API (using FastAPI)
# Covers: User Management, Natal Chart, Transit Chart, Aspects, Daily Vibe, Chat, Preferences, Mood Check-In

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import swisseph as swe
import datetime
import pytz
import os
import uuid
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
import supabase_helpers as sb
from memory.tiny_memory import TinyMemory
from chains.multi_prompt_chain import MultiPromptManager
from chains.classifier import classify_message

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# LangChain + OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableSequence

app = FastAPI(title="Astrology API with Swiss Ephemeris")

# Set Swiss Ephemeris path
EPHE_PATH = os.environ.get("EPHE_PATH", "./ephe")
swe.set_ephe_path(EPHE_PATH)
memory_manager = TinyMemory()
multi_prompt_manager = MultiPromptManager(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_API_KEY")
)

PLANETS = [
    swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
    swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO
]

PLANET_NAMES = {
    swe.SUN: "Sun", swe.MOON: "Moon", swe.MERCURY: "Mercury", swe.VENUS: "Venus",
    swe.MARS: "Mars", swe.JUPITER: "Jupiter", swe.SATURN: "Saturn",
    swe.URANUS: "Uranus", swe.NEPTUNE: "Neptune", swe.PLUTO: "Pluto"
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Mock in-memory DB
USERS_DB = {}
ASTRO_PROFILES_DB = {}
DAILY_CONTEXT_DB = {}
CHAT_HISTORY_DB = {}
PREFERENCES_DB = {}
MOOD_LOG_DB = {}

class BirthData(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    timezone: str

class User(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    birth_data: BirthData

class AspectData(BaseModel):
    birth_year: int
    birth_month: int
    birth_day: int
    birth_hour: int
    birth_minute: int
    birth_timezone: str
    transit_year: int
    transit_month: int
    transit_day: int
    transit_hour: int
    transit_minute: int
    transit_timezone: str

class Message(BaseModel):
    user_id: str
    message: str

class Preference(BaseModel):
    user_id: str
    preferences: Dict[str, str]

class MoodCheckIn(BaseModel):
    user_id: str
    mood_score: int
    note: Optional[str] = ""

class UserIdRequest(BaseModel):
    user_id: str

def get_julian_day(year, month, day, hour, minute, tz):
    dt = datetime.datetime(year, month, day, hour, minute)
    dt_utc = pytz.timezone(tz).localize(dt).astimezone(pytz.utc)
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0)

def calculate_planet_positions(jd):
    positions = {}
    for planet in PLANETS:
        lon, _ = swe.calc_ut(jd, planet)
        positions[PLANET_NAMES[planet]] = round(lon[0], 2)
    return positions

def determine_sign(lon):
    return ZODIAC_SIGNS[int(lon // 30)]

def calculate_rising_sign(jd, lat, lon):
    # Placeholder for now, we would use more advanced logic for rising sign
    return "Leo"  # Placeholder

def calculate_aspects(natal_positions, transit_positions):
    # Placeholder logic to calculate basic aspects (e.g., conjunction, square, opposition)
    aspects = []
    for planet_name, natal_pos in natal_positions.items():
        for transit_planet, transit_pos in transit_positions.items():
            if abs(natal_pos - transit_pos) < 10:  # Conjunction
                aspects.append(f"Conjunction with {planet_name}")
            elif abs(natal_pos - transit_pos) > 90 and abs(natal_pos - transit_pos) < 110:  # Square
                aspects.append(f"Square with {planet_name}")
            elif abs(natal_pos - transit_pos) > 170 and abs(natal_pos - transit_pos) < 190:  # Opposition
                aspects.append(f"Opposition with {planet_name}")
    return aspects

def get_traits_by_sign(sign):
    traits = {
        "Aries": "Bold, energetic, pioneering",
        "Taurus": "Grounded, patient, loyal",
        "Gemini": "Curious, witty, adaptable",
        "Cancer": "Sensitive, nurturing, protective",
        "Leo": "Confident, creative, proud",
        "Virgo": "Analytical, practical, diligent",
        "Libra": "Charming, balanced, fair-minded",
        "Scorpio": "Intense, intuitive, passionate",
        "Sagittarius": "Adventurous, optimistic, independent",
        "Capricorn": "Disciplined, ambitious, wise",
        "Aquarius": "Innovative, independent, humanitarian",
        "Pisces": "Compassionate, dreamy, artistic"
    }
    return traits.get(sign, "")

@app.get("/")
def read_root():
    return {"message": "Astro API is live!"}

@app.post("/users")
def create_user(user: User):
    # Generate UUID if not provided
    user_data = user.dict()
    if not user_data.get("user_id"):
        user_data["user_id"] = str(uuid.uuid4())
    
    try:
        result = sb.create_user(supabase, user_data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create user")
        return {"status": "created", "user_id": user_data["user_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}")
def get_user(user_id: str):
    result = sb.get_user(supabase, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@app.post("/astro-profiles/generate")
def generate_astro_profile_by_user(req: UserIdRequest):
    user = sb.get_user(supabase, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    jd = get_julian_day(
        user['birth_data']['year'], user['birth_data']['month'], user['birth_data']['day'],
        user['birth_data']['hour'], user['birth_data']['minute'], user['birth_data']['timezone']
    )
    positions = calculate_planet_positions(jd)
    sun_sign = determine_sign(positions["Sun"])
    moon_sign = determine_sign(positions["Moon"])
    rising_sign = "Leo"  # TODO: Calculate properly

    profile = {
        "user_id": req.user_id,
        "sun_sign": sun_sign,
        "moon_sign": moon_sign,
        "rising_sign": rising_sign,
        "natal_chart": positions
    }

    sb.save_astro_profile(supabase, req.user_id, profile)
    return profile

@app.get("/astro-profiles/{user_id}")
def get_astro_profile(user_id: str):
    profile = sb.get_astro_profile(supabase, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Astro profile not found")
    return profile

@app.post("/daily-context/generate")
def generate_daily_context(req: UserIdRequest):
    profile = sb.get_astro_profile(supabase, req.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Astro profile not found")

    today = datetime.datetime.now()
    jd = get_julian_day(today.year, today.month, today.day, today.hour, today.minute, "UTC")
    transits = calculate_planet_positions(jd)
    aspects = calculate_aspects(profile["natal_chart"], transits)

    context = {
        "user_id": req.user_id,
        "date": today.strftime("%Y-%m-%d"),
        "mood_score": 7,  # Placeholder
        "transits": transits,
        "aspects_today": aspects,
        "summary": "Moon in Cancer brings emotional sensitivity..."
    }

    sb.save_daily_context(supabase, req.user_id, context)
    return context

@app.get("/daily-context/{user_id}/{date}")
def get_daily_context(user_id: str, date: str):
    context = sb.get_daily_context(supabase, user_id, date)
    if not context:
        raise HTTPException(status_code=404, detail="Daily context not found")
    return context

@app.post("/chat/message")
def chat_message(msg: Message):
    logger.debug(f"Received message from user {msg.user_id}: {msg.message}")

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    vibe = sb.get_daily_context(supabase, msg.user_id, today) or {}
    profile = sb.get_astro_profile(supabase, msg.user_id) or {}

    logger.debug(f"Profile: {profile}, Vibe: {vibe}")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key")

    # Prepare extra context
    extra_context = {
        "sun_sign": profile.get("sun_sign", ""),
        "moon_sign": profile.get("moon_sign", ""),
        "rising_sign": profile.get("rising_sign", ""),
        "summary": vibe.get("summary", ""),
        "aspects": ", ".join(vibe.get("aspects_today", [])),
    }

    # Build enhanced input
    enhanced_user_message = (
        f"User Message: {msg.message}\n"
        f"Sun Sign: {extra_context['sun_sign']}, Moon Sign: {extra_context['moon_sign']}, Rising: {extra_context['rising_sign']}\n"
        f"Today's Vibe Summary: {extra_context['summary']}\n"
        f"Important Aspects Today: {extra_context['aspects']}"
    )

    # Classify the message
    message_type = classify_message(msg.message)
    logger.debug(f"Classified message type: {message_type}")

    # Run multi prompt manager
    response_text = multi_prompt_manager.run(
        user_id=msg.user_id,
        user_message=enhanced_user_message,
        memory_manager=memory_manager,
        force_type=message_type  # <- we'll add this option
    )

    # Save chat to Supabase
    sb.add_chat_message(supabase, msg.user_id, "user", msg.message)
    sb.add_chat_message(supabase, msg.user_id, "ai", response_text)

    logger.debug(f"Final AI response: {response_text}")
    return {"response": response_text}

@app.get("/chat/history/{user_id}")
def get_chat_history_api(user_id: str, limit: int = 50, offset: int = 0):
    try:
        chats = sb.get_chat_history(supabase, user_id, limit, offset)
        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preferences")
def save_preferences(pref: Preference):
    sb.save_preferences(supabase, pref.user_id, pref.preferences)
    return {"status": "saved"}

@app.get("/preferences/{user_id}")
def get_preferences(user_id: str):
    result = sb.get_preferences(supabase, user_id)
    if not result:
        return {}
    return result.get("preferences", {})

@app.post("/mood/check-in")
def mood_checkin(data: MoodCheckIn):
    sb.log_mood_checkin(supabase, data.user_id, data.mood_score, data.note)
    return {"status": "mood logged"}

# To run: `uvicorn astro_api:app --reload`
