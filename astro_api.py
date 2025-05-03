# Astrology API (using FastAPI)
# Covers: User Management, Moods, Companion Energies, Cosmic Energy Cards, Chat, Subscriptions

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
import datetime
import os
import logging
import json
from uuid import UUID, uuid4
from dotenv import load_dotenv
from supabase import create_client, Client
import supabase_helpers as sb
from memory.tiny_memory import TinyMemory
from chains.multi_prompt_chain import MultiPromptManager
from chains.classifier import classify_message

# Custom JSON encoder to handle date and datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

# Custom JSONResponse class using our encoder
class CustomJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

# Import our new models
from models import (
    UserBase, UserCreate, UserResponse,
    MoodBase, MoodCreate, MoodResponse,
    UserMoodBase, UserMoodCreate, UserMoodResponse,
    CompanionEnergyBase, CompanionEnergyCreate, CompanionEnergyResponse,
    UserCompanionEnergyBase, UserCompanionEnergyCreate, UserCompanionEnergyResponse,
    CosmicEnergyTypeBase, CosmicEnergyTypeCreate, CosmicEnergyTypeResponse,
    CosmicEnergyCardBase, CosmicEnergyCardCreate, CosmicEnergyCardResponse,
    UserCosmicEnergyCardBase, UserCosmicEnergyCardCreate, UserCosmicEnergyCardResponse,
    ConversationBase, ConversationCreate, ConversationResponse,
    MessageBase, MessageCreate, MessageResponse,
    SubscriptionBase, SubscriptionCreate, SubscriptionResponse,
    UserIdRequest, MessageRequest, MoodCheckInRequest, CompanionEnergyRequest,
    CosmicEnergyCardRequest, ConversationRequest, MessageSendRequest
)

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

app = FastAPI(
    title="Astrology API",
    description="API for astrological insights, user profiles, and AI chat",
    version="1.0.0",
    default_response_class=CustomJSONResponse
)

# Initialize memory manager and prompt manager
memory_manager = TinyMemory()
multi_prompt_manager = MultiPromptManager(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Supabase client with custom JSON encoder
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
            return obj.isoformat()
        return super().default(obj)

# Monkey patch json.dumps to use our encoder
original_dumps = json.dumps
def patched_dumps(*args, **kwargs):
    kwargs.setdefault('cls', JSONEncoder)
    return original_dumps(*args, **kwargs)

json.dumps = patched_dumps

# Use real Supabase data
DEV_MODE = False

# Initialize Supabase client with the service role key to bypass RLS
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Zodiac signs reference
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Helper functions for the new API

def get_zodiac_sign(birth_date):
    # Convert string to date object if needed
    if isinstance(birth_date, str):
        try:
            # Try to parse the date string
            birth_date = datetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
        except Exception as e:
            logger.error(f"Error parsing birth date: {str(e)}")
            # Default to Aries if we can't parse the date
            return "Aries"
    
    month = birth_date.month
    day = birth_date.day
    
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "Aries"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "Taurus"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "Gemini"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "Cancer"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "Leo"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "Virgo"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "Libra"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "Scorpio"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "Sagittarius"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "Capricorn"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "Aquarius"
    else:
        return "Pisces"

def get_zodiac_traits(sign):
    """Get traits for a zodiac sign"""
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

# User endpoints
def serialize_for_db(data):
    """Helper function to convert non-serializable objects to strings"""
    if isinstance(data, dict):
        return {k: serialize_for_db(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_for_db(item) for item in data]
    elif isinstance(data, (datetime.date, datetime.datetime, datetime.time)):
        return data.isoformat()
    elif isinstance(data, UUID):
        return str(data)
    else:
        return data

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate):
    # Convert model to dict and handle serialization
    user_data = serialize_for_db(user.dict())
    
    try:
        # Remove any id field if present - let Supabase generate it
        if "id" in user_data:
            del user_data["id"]
        
        # Try to insert the user data
        result = supabase.table('users').insert(user_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create user")

        # Create a default conversation for the user
        try:
            user_id = result.data[0]["id"]
            logger.info(f"Creating default conversation for user: {user_id}")
            
            conversation_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "title": "Welcome",
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            logger.info(f"Conversation data: {conversation_data}")
            
            # Save conversation to database
            try:
                conversation_result = supabase.table('conversations').insert(conversation_data).execute()
                logger.info(f"Conversation creation result: {conversation_result.data}")
                
                if conversation_result.data:
                    logger.info(f"Created default conversation for user: {user_id}")
                    
                    # Create a welcome message from the assistant
                    welcome_message = {
                        "id": str(uuid4()),
                        "conversation_id": conversation_data["id"],
                        "content": "Welcome to Astro! I'm your personal cosmic companion. How can I assist you today?",
                        "role": "assistant",
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    logger.info(f"Welcome message data: {welcome_message}")
                    
                    # Save welcome message to database
                    try:
                        message_result = supabase.table('messages').insert(welcome_message).execute()
                        logger.info(f"Message creation result: {message_result.data}")
                        
                        if message_result.data:
                            logger.info(f"Created welcome message for user: {user_id}")
                    except Exception as msg_error:
                        logger.error(f"Error creating welcome message: {str(msg_error)}")
            except Exception as conv_error:
                logger.error(f"Error creating conversation: {str(conv_error)}")
        except Exception as e:
            # Log the error but don't fail the user creation
            logger.error(f"Error creating default conversation: {str(e)}")
            logger.error(f"Error details: {type(e).__name__}")
            import traceback
            logger.error(traceback.format_exc())

        logger.info(f"Created user: {result.data[0]}")
        return result.data[0]
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID):
    try:
        # Get user from Supabase
        try:
            result = supabase.table('users').select("*").eq("id", str(user_id)).single().execute()
            if not result.data:
                raise HTTPException(status_code=404, detail="User not found")
            return result.data
        except Exception as e:
            # Check if this is a "no rows" error
            if "no rows" in str(e).lower() or "0 rows" in str(e).lower() or "PGRST116" in str(e):
                raise HTTPException(status_code=404, detail="User not found")
            # For other errors, re-raise
            logger.error(f"Error getting user: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Mood endpoints
@app.get("/moods", response_model=List[MoodResponse])
def get_moods():
    try:
        result = supabase.table('moods').select("*").execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user-moods", response_model=UserMoodResponse, status_code=201)
def create_user_mood(mood: UserMoodCreate):
    try:
        # Check if user exists
        try:
            user_result = supabase.table('users').select("*").eq("id", str(mood.user_id)).single().execute()
            if not user_result.data:
                raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            # Check if this is a row-level security error or no rows error
            if "row-level security" in str(e).lower() or "42501" in str(e) or "no rows" in str(e).lower():
                raise HTTPException(status_code=404, detail="User not found")
            raise
        
        # Check if mood exists
        try:
            mood_result = supabase.table('moods').select("*").eq("id", str(mood.mood_id)).single().execute()
            if not mood_result.data:
                raise HTTPException(status_code=404, detail="Mood not found")
        except Exception as e:
            # Check if this is a row-level security error or no rows error
            if "row-level security" in str(e).lower() or "42501" in str(e) or "no rows" in str(e).lower():
                raise HTTPException(status_code=404, detail="Mood not found")
            raise
        
        # Create user mood entry
        mood_data = mood.dict()
        # Remove any id field if present - let Supabase generate it
        if "id" in mood_data:
            del mood_data["id"]
        mood_data["date"] = datetime.datetime.now()
        
        # Serialize all non-JSON serializable objects
        mood_data = serialize_for_db(mood_data)
        
        try:
            result = supabase.table('user_moods').insert(mood_data).execute()
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create user mood")
            
            # Return with mood details included
            response_data = result.data[0]
            response_data["mood"] = mood_result.data
            return response_data
        except Exception as e:
            # Check if this is a row-level security error
            if "row-level security" in str(e).lower() or "42501" in str(e):
                # Try to authenticate first
                try:
                    # For development purposes, we'll try to sign in as the user
                    # This is a workaround for RLS policies
                    # First, try to get an existing user with the same ID
                    anon_client = create_client(
                        os.getenv("SUPABASE_URL"),
                        os.getenv("SUPABASE_API_KEY")
                    )
                    
                    # Try inserting with the anonymous client
                    anon_result = anon_client.table('user_moods').insert(mood_data).execute()
                    
                    if not anon_result.data:
                        raise HTTPException(status_code=500, detail="Failed to create user mood")
                    
                    # Return with mood details included
                    response_data = anon_result.data[0]
                    response_data["mood"] = mood_result.data
                    return response_data
                except Exception as inner_e:
                    logger.error(f"Error creating user mood with anonymous client: {str(inner_e)}")
                    raise HTTPException(status_code=500, detail="Failed to create user mood")
            else:
                raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user mood: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user-moods/{user_id}", response_model=List[UserMoodResponse])
def get_user_moods(user_id: UUID, limit: int = 10):
    try:
        # Get user moods with mood details
        try:
            result = supabase.table('user_moods').select(
                "*, moods(*)"
            ).eq("user_id", str(user_id)).order("date", desc=True).limit(limit).execute()
            
            # If no moods found, return empty list
            if not result.data:
                return []
            
            # Format response to match our model
            response_data = []
            for item in result.data:
                mood_data = item.pop("moods", {})
                item["mood"] = mood_data
                response_data.append(item)
                
            return response_data
        except Exception as e:
            # Check if this is a "no rows" error
            if "no rows" in str(e).lower() or "0 rows" in str(e).lower():
                return []
            # Check if this is a row-level security error
            elif "row-level security" in str(e).lower() or "42501" in str(e):
                # For development, we'll just return an empty list
                logger.warning(f"Row-level security error when getting user moods: {str(e)}")
                return []
            else:
                raise
    except Exception as e:
        logger.error(f"Error getting user moods: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Companion Energy endpoints
@app.get("/companion-energies", response_model=List[CompanionEnergyResponse])
def get_companion_energies():
    try:
        result = supabase.table('companion_energies').select("*").execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user-companion-energies", response_model=UserCompanionEnergyResponse, status_code=201)
def set_user_companion_energy(energy: UserCompanionEnergyCreate):
    try:
        # Check if user exists
        user_result = supabase.table('users').select("*").eq("id", str(energy.user_id)).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if companion energy exists
        energy_result = supabase.table('companion_energies').select("*").eq("id", str(energy.companion_energy_id)).single().execute()
        if not energy_result.data:
            raise HTTPException(status_code=404, detail="Companion energy not found")
        
        # Deactivate any existing active companion energies for this user
        supabase.table('user_companion_energies').update({"is_active": False}).eq("user_id", str(energy.user_id)).eq("is_active", True).execute()
        
        # Create new user companion energy entry
        energy_data = energy.dict()
        energy_data["id"] = uuid4()
        
        result = supabase.table('user_companion_energies').insert(energy_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to set user companion energy")
        
        # Return with companion energy details included
        response_data = result.data[0]
        response_data["companion_energy"] = energy_result.data
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user-companion-energies/{user_id}", response_model=UserCompanionEnergyResponse)
def get_user_companion_energy(user_id: UUID):
    try:
        # Get active companion energy for user with energy details
        result = supabase.table('user_companion_energies').select(
            "*, companion_energies(*)"
        ).eq("user_id", str(user_id)).eq("is_active", True).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Active companion energy not found for user")
        
        # Format response to match our model
        response_data = result.data
        energy_data = response_data.pop("companion_energies", {})
        response_data["companion_energy"] = energy_data
            
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Cosmic Energy endpoints
@app.get("/cosmic-energy-types", response_model=List[CosmicEnergyTypeResponse])
def get_cosmic_energy_types():
    try:
        result = supabase.table('cosmic_energy_types').select("*").execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cosmic-energy-cards", response_model=List[CosmicEnergyCardResponse])
def get_cosmic_energy_cards(zodiac_sign: Optional[str] = None, date: Optional[str] = None):
    try:
        query = supabase.table('cosmic_energy_cards').select("*, cosmic_energy_types(*)")
        
        # Apply filters if provided
        if zodiac_sign:
            query = query.eq("zodiac_sign", zodiac_sign)
        
        if date:
            query = query.eq("date", date)
        else:
            # Default to today's date
            today = datetime.date.today().isoformat()
            query = query.eq("date", today)
        
        result = query.execute()
        
        # Format response to match our model
        response_data = []
        for item in result.data:
            energy_type_data = item.pop("cosmic_energy_types", {})
            item["energy_type"] = energy_type_data
            response_data.append(item)
            
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user-cosmic-energy-cards", response_model=UserCosmicEnergyCardResponse, status_code=201)
def mark_card_as_read(card: UserCosmicEnergyCardCreate):
    try:
        # Check if user exists
        user_result = supabase.table('users').select("*").eq("id", str(card.user_id)).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if card exists
        card_result = supabase.table('cosmic_energy_cards').select("*").eq("id", str(card.card_id)).single().execute()
        if not card_result.data:
            raise HTTPException(status_code=404, detail="Cosmic energy card not found")
        
        # Create or update user card entry
        card_data = card.dict()
        card_data["id"] = uuid4()
        
        result = supabase.table('user_cosmic_energy_cards').insert(card_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to mark card as read")
        
        # Return with card details included
        response_data = result.data[0]
        response_data["card"] = card_result.data
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{user_id}", response_model=List[ConversationResponse])
def get_user_conversations(user_id: UUID):
    try:
        logger.info(f"Getting conversations for user: {user_id}")
        result = supabase.table('conversations').select("*").eq("user_id", str(user_id)).order("updated_at", desc=True).execute()
        logger.info(f"Found {len(result.data)} conversations for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"Error in get_user_conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(conversation: ConversationCreate):
    try:
        # Serialize the data for Supabase
        conversation_data = serialize_for_db(conversation.dict())
        
        # Add ID and timestamps if not present
        if "id" not in conversation_data:
            conversation_data["id"] = str(uuid4())
        
        now = datetime.datetime.now().isoformat()
        if "created_at" not in conversation_data:
            conversation_data["created_at"] = now
        if "updated_at" not in conversation_data:
            conversation_data["updated_at"] = now
        
        # Save conversation to database
        result = supabase.table('conversations').insert(conversation_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create conversation")
        
        return result.data[0]
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Message endpoints
@app.post("/messages", response_model=MessageResponse, status_code=201)
def send_message(message: MessageSendRequest):
    try:
        # Serialize the data for Supabase
        message_data = serialize_for_db(message.dict())
        
        # Check if conversation exists
        try:
            conversation_result = supabase.table('conversations').select("*").eq("id", str(message.conversation_id)).execute()
            
            # Check if we got any data back
            if not conversation_result.data or len(conversation_result.data) == 0:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Use the first conversation found
            conversation = conversation_result.data[0]
        except Exception as e:
            if "no rows" in str(e).lower() or "0 rows" in str(e).lower() or "PGRST116" in str(e):
                raise HTTPException(status_code=404, detail="Conversation not found")
            else:
                raise
        
        # Create message
        if "id" not in message_data:
            message_data["id"] = str(uuid4())
        message_data["timestamp"] = datetime.datetime.now().isoformat()
        
        # Save message to database
        result = supabase.table('messages').insert(message_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to send message")
        
        # If this is a user message, generate AI response
        if message.role == "user":
            # Get user details for context
            user_id = conversation["user_id"]
            try:
                user_result = supabase.table('users').select("*").eq("id", user_id).execute()
                
                if user_result.data and len(user_result.data) > 0:
                    user = user_result.data[0]
                    zodiac_sign = get_zodiac_sign(user["birth_date"])
                    zodiac_traits = get_zodiac_traits(zodiac_sign)
                    
                    # Get user's active companion energy
                    try:
                        energy_result = supabase.table('user_companion_energies').select(
                            "*, companion_energies(*)"
                        ).eq("user_id", user_id).eq("is_active", True).execute()
                        
                        companion_energy = "Wise & Calm"
                        if energy_result.data and len(energy_result.data) > 0:
                            companion_energy = energy_result.data[0]["companion_energies"]["name"]
                    except Exception as e:
                        logger.warning(f"Error getting companion energy: {str(e)}")
                        companion_energy = "Wise & Calm"
                    
                    # Prepare context for AI
                    context = f"User's zodiac sign: {zodiac_sign}\nZodiac traits: {zodiac_traits}\nCompanion energy: {companion_energy}\n"
                    
                    # Get conversation history
                    try:
                        history_result = supabase.table('messages').select("*").eq("conversation_id", str(message.conversation_id)).order("timestamp").limit(10).execute()
                        history = history_result.data if history_result.data else []
                    except Exception as e:
                        logger.warning(f"Error getting conversation history: {str(e)}")
                        history = []
                    
                    # Format history for the AI
                    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                    
                    # Classify message type
                    message_type = classify_message(message.content)
                    
                    # Generate AI response
                    enhanced_user_message = f"{context}\nConversation history:\n{history_text}\nUser message: {message.content}"
                    
                    logger.info(f"Generating AI response for message: {message.content}")
                    logger.info(f"Message type: {message_type}")
                    logger.info(f"Enhanced user message: {enhanced_user_message}")
                    
                    try:
                        ai_response = multi_prompt_manager.run(
                            user_id=user_id,
                            user_message=enhanced_user_message,
                            memory_manager=memory_manager,
                            force_type=message_type
                        )
                        logger.info(f"AI response generated: {ai_response}")
                    except Exception as e:
                        logger.error(f"Error generating AI response: {str(e)}")
                        ai_response = "I'm sorry, I couldn't generate a response at this time. Please try again later."
                    
                    # Save AI response
                    ai_message = {
                        "id": str(uuid4()),
                        "conversation_id": str(message.conversation_id),
                        "content": ai_response,
                        "role": "assistant",
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    try:
                        logger.info(f"Saving AI response to database: {ai_message}")
                        ai_result = supabase.table('messages').insert(ai_message).execute()
                        logger.info(f"AI response saved: {ai_result.data}")
                    except Exception as e:
                        logger.error(f"Error saving AI response: {str(e)}")
                    
                    # Update conversation timestamp
                    try:
                        supabase.table('conversations').update({"updated_at": datetime.datetime.now().isoformat()}).eq("id", str(message.conversation_id)).execute()
                    except Exception as e:
                        logger.error(f"Error updating conversation timestamp: {str(e)}")
                    
                    # Store the AI response to return it later
                    return_data = result.data[0]
                    return_data["assistant_response"] = ai_message
            except Exception as e:
                logger.error(f"Error processing user message: {str(e)}")
                # Continue without AI response
        
        # Check if we have an assistant response to return
        if "assistant_response" in locals():
            return return_data
        else:
            return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/messages/{conversation_id}", response_model=List[MessageResponse])
def get_conversation_messages(conversation_id: UUID):
    try:
        result = supabase.table('messages').select("*").eq("conversation_id", str(conversation_id)).order("timestamp").execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Subscription endpoints
@app.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
def create_subscription(subscription: SubscriptionCreate):
    try:
        # Check if user exists
        user_result = supabase.table('users').select("*").eq("id", str(subscription.user_id)).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create subscription
        subscription_data = subscription.dict()
        subscription_data["id"] = uuid4()
        
        result = supabase.table('subscriptions').insert(subscription_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create subscription")
        
        # Update user premium status
        supabase.table('users').update({"is_premium": True}).eq("id", str(subscription.user_id)).execute()
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subscriptions/{user_id}", response_model=List[SubscriptionResponse])
def get_user_subscriptions(user_id: UUID):
    try:
        result = supabase.table('subscriptions').select("*").eq("user_id", str(user_id)).order("start_date", desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# To run: `uvicorn astro_api:app --reload`
