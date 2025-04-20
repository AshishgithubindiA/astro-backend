# Swiss Ephemeris Astrology API (using FastAPI)
# Covers: User Management, Natal Chart, Transit Chart, Aspects, Daily Vibe, Chat, Preferences, Mood Check-In

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from dotenv import load_dotenv
import swisseph as swe
import datetime
import pytz
import os
import uuid
import logging
# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# LangChain + OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableSequence

load_dotenv()  # Loads from .env into environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Astrology API with Swiss Ephemeris")

# Set Swiss Ephemeris path
EPHE_PATH = os.environ.get("EPHE_PATH", "./ephe")
swe.set_ephe_path(EPHE_PATH)

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
    user_id: str
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

@app.post("/users")
def create_user(user: User):
    USERS_DB[user.user_id] = user
    return {"status": "created", "user_id": user.user_id}

@app.get("/users/{user_id}")
def get_user(user_id: str):
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/astro-profiles/generate")
def generate_astro_profile_by_user(req: UserIdRequest):
    user = USERS_DB.get(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    birth = user.birth_data
    jd = get_julian_day(birth.year, birth.month, birth.day, birth.hour, birth.minute, birth.timezone)
    positions = calculate_planet_positions(jd)
    sun_sign = determine_sign(positions["Sun"])
    moon_sign = determine_sign(positions["Moon"])
    rising_sign = "Leo"  # Placeholder, real calculation requires more details
    profile = {
        "sun_sign": sun_sign,
        "moon_sign": moon_sign,
        "rising_sign": rising_sign,
        "natal_chart": positions
    }
    ASTRO_PROFILES_DB[req.user_id] = profile
    return profile

@app.get("/astro-profiles/{user_id}")
def get_astro_profile(user_id: str):
    profile = ASTRO_PROFILES_DB.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Astro profile not found")
    return profile

@app.post("/daily-context/generate")
def generate_daily_context(req: UserIdRequest):
    user = USERS_DB.get(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    today = datetime.datetime.now()
    jd = get_julian_day(today.year, today.month, today.day, today.hour, today.minute, "UTC")
    transits = calculate_planet_positions(jd)
    aspects = calculate_aspects(ASTRO_PROFILES_DB[req.user_id]["natal_chart"],transits)  # Placeholder
    context = {
        "date": today.strftime("%Y-%m-%d"),
        "mood_score": 7,
        "transits": transits,
        "aspects_today": aspects,
        "summary": "Moon in Cancer brings emotional sensitivity..."
    }
    DAILY_CONTEXT_DB[f"{req.user_id}:{context['date']}"] = context
    return context

@app.get("/daily-context/{user_id}/{date}")
def get_daily_context(user_id: str, date: str):
    context = DAILY_CONTEXT_DB.get(f"{user_id}:{date}")
    if not context:
        raise HTTPException(status_code=404, detail="Daily context not found")
    return context

@app.post("/chat/message")
def chat_message(msg: Message):
    # Log the incoming user message
    logger.debug(f"Received message from user {msg.user_id}: {msg.message}")
    
    CHAT_HISTORY_DB.setdefault(msg.user_id, []).append({"role": "user", "text": msg.message})

    # Fetch vibe context
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    vibe = DAILY_CONTEXT_DB.get(f"{msg.user_id}:{today}", {})
    profile = ASTRO_PROFILES_DB.get(msg.user_id, {})

    # Log the vibe and profile data
    logger.debug(f"User's astro profile: {profile}")
    logger.debug(f"Today's vibe: {vibe}")

    # Make sure the OpenAI API key is passed via env or securely
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key")

    # Prepare inputs for the prompt
    inputs = {
        "sun_sign": profile.get("sun_sign", ""),
        "moon_sign": profile.get("moon_sign", ""),
        "rising_sign": profile.get("rising_sign", ""),
        "summary": vibe.get("summary", ""),
        "aspects": ", ".join(vibe.get("aspects_today", [])),
        "user_msg": msg.message
    }

    # Log the final inputs before creating the prompt
    logger.debug(f"Prompt inputs: {inputs}")

    # Prepare the full prompt
    # Prepare the full prompt
    prompt = [
        SystemMessage(content="You are a friendly astrology expert AI. Summarise answer in 2-3 sentences"),
        HumanMessage(content=f"Based on this user's astro profile: Sun Sign: {inputs['sun_sign']}, Moon Sign: {inputs['moon_sign']}, Rising Sign: {inputs['rising_sign']}, and today's vibe: Summary: {inputs['summary']}, Aspects: {inputs['aspects']}. Respond to the user message with empathy and astrological insight."),
        HumanMessage(content=inputs['user_msg'])
    ]

    # Log the constructed prompt content
    logger.debug(f"Constructed prompt content: {prompt}")

    # Create the ChatOpenAI instance (GPT-4o-mini)
    chat = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=openai_api_key)

    # Send the prompt to the model
    response = chat.generate([prompt])

    # Log the response from the model
    logger.debug(f"Response from GPT-4o-mini: {response}")

    # Access the response text correctly
    response_text = response.generations[0][0].text  # Accessing the first generation and then the text

    CHAT_HISTORY_DB[msg.user_id].append({"role": "ai", "text": response_text})

    # Log the final AI response
    logger.debug(f"Final response: {response_text}")

    return {"response": response_text}

@app.get("/chat/history/{user_id}")
def chat_history(user_id: str):
    return CHAT_HISTORY_DB.get(user_id, [])

@app.post("/preferences")
def save_preferences(pref: Preference):
    PREFERENCES_DB[pref.user_id] = pref.preferences
    return {"status": "saved"}

@app.get("/preferences/{user_id}")
def get_preferences(user_id: str):
    return PREFERENCES_DB.get(user_id, {})

@app.post("/mood/check-in")
def mood_checkin(data: MoodCheckIn):
    MOOD_LOG_DB.setdefault(data.user_id, []).append({
        "mood_score": data.mood_score,
        "note": data.note,
        "timestamp": datetime.datetime.now().isoformat()
    })
    return {"status": "mood logged"}

# To run: `uvicorn astro_api:app --reload`
