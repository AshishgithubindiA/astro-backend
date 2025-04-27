def classify_message(user_message: str) -> str:
    text = user_message.lower()

    if any(word in text for word in ["mood", "feeling", "emotion", "energy today", "energy check"]):
        return "mood_checkin"
    
    if any(word in text for word in ["love", "relationship", "partner", "crush", "dating", "soulmate"]):
        return "relationship"
    
    if any(word in text for word in ["career", "life purpose", "goal", "future", "direction", "growth"]):
        return "life_advice"
    
    if any(word in text for word in ["today", "vibe", "astrology today", "horoscope", "daily vibe"]):
        return "daily_vibe"
    
    return "default"  # fallback
