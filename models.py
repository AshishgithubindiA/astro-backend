from pydantic import BaseModel, Field, EmailStr
from typing import Dict, List, Optional, Any, Union
from datetime import date, time, datetime
from uuid import UUID, uuid4
from decimal import Decimal

# User models
class UserBase(BaseModel):
    name: str
    pronouns: str
    birth_date: date
    birth_time: Optional[time] = None
    birth_place: str
    email: Optional[EmailStr] = None
    profile_picture_url: Optional[str] = None
    is_premium: Optional[bool] = False

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Mood models
class MoodBase(BaseModel):
    name: str
    emoji: str
    description: str
    color: str

class MoodCreate(MoodBase):
    pass

class MoodResponse(MoodBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User Mood models
class UserMoodBase(BaseModel):
    user_id: UUID
    mood_id: UUID

class UserMoodCreate(UserMoodBase):
    pass

class UserMoodResponse(UserMoodBase):
    id: UUID
    date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    mood: Optional[MoodResponse] = None

    class Config:
        from_attributes = True

# Companion Energy models
class CompanionEnergyBase(BaseModel):
    name: str
    emoji: str
    description: str

class CompanionEnergyCreate(CompanionEnergyBase):
    pass

class CompanionEnergyResponse(CompanionEnergyBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User Companion Energy models
class UserCompanionEnergyBase(BaseModel):
    user_id: UUID
    companion_energy_id: UUID
    is_active: Optional[bool] = True

class UserCompanionEnergyCreate(UserCompanionEnergyBase):
    pass

class UserCompanionEnergyResponse(UserCompanionEnergyBase):
    id: UUID
    created_at: Optional[datetime] = None
    companion_energy: Optional[CompanionEnergyResponse] = None

    class Config:
        from_attributes = True

# Cosmic Energy Type models
class CosmicEnergyTypeBase(BaseModel):
    name: str
    emoji: str
    background_color: str

class CosmicEnergyTypeCreate(CosmicEnergyTypeBase):
    pass

class CosmicEnergyTypeResponse(CosmicEnergyTypeBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Cosmic Energy Card models
class CosmicEnergyCardBase(BaseModel):
    type_id: UUID
    insight: str
    extended_insight: Optional[str] = None
    zodiac_sign: str
    date: date

class CosmicEnergyCardCreate(CosmicEnergyCardBase):
    pass

class CosmicEnergyCardResponse(CosmicEnergyCardBase):
    id: UUID
    created_at: Optional[datetime] = None
    energy_type: Optional[CosmicEnergyTypeResponse] = None

    class Config:
        from_attributes = True

# User Cosmic Energy Card models
class UserCosmicEnergyCardBase(BaseModel):
    user_id: UUID
    card_id: UUID
    is_read: Optional[bool] = False

class UserCosmicEnergyCardCreate(UserCosmicEnergyCardBase):
    pass

class UserCosmicEnergyCardResponse(UserCosmicEnergyCardBase):
    id: UUID
    created_at: Optional[datetime] = None
    card: Optional[CosmicEnergyCardResponse] = None

    class Config:
        from_attributes = True

# Conversation models
class ConversationBase(BaseModel):
    user_id: UUID
    title: Optional[str] = None

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Message models
class MessageBase(BaseModel):
    conversation_id: UUID
    content: str
    role: str  # 'user', 'assistant', or 'system'

class MessageCreate(MessageBase):
    pass

class MessageSendRequest(BaseModel):
    conversation_id: UUID
    content: str
    role: str = "user"  # Default to 'user'
    user_id: Optional[UUID] = None  # Optional user_id for development mode

class MessageResponse(MessageBase):
    id: UUID
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    assistant_response: Optional[dict] = None

    class Config:
        from_attributes = True

# Subscription models
class SubscriptionBase(BaseModel):
    user_id: UUID
    plan_name: str
    price: Decimal
    billing_period: str  # 'weekly', 'monthly', or 'yearly'
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = True

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionResponse(SubscriptionBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Request models
class UserIdRequest(BaseModel):
    user_id: UUID

class MessageRequest(BaseModel):
    user_id: UUID
    message: str

class MoodCheckInRequest(BaseModel):
    user_id: UUID
    mood_id: UUID

class CompanionEnergyRequest(BaseModel):
    user_id: UUID
    companion_energy_id: UUID

class CosmicEnergyCardRequest(BaseModel):
    user_id: UUID
    date: Optional[date] = None
    zodiac_sign: Optional[str] = None

class ConversationRequest(BaseModel):
    user_id: UUID
    title: Optional[str] = None

class MessageSendRequest(BaseModel):
    conversation_id: UUID
    content: str
    role: str = 'user'