from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
import random

from chains.prompts import (
    daily_vibe_prompt,
    life_advice_prompt,
    mood_checkin_prompt,
    relationship_prompt,
    default_prompt
)
from chains.classifier import classify_message

class MultiPromptManager:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.7, 
            api_key=openai_api_key,
            max_tokens=75
        )

        # Map types to prompts
        self.prompt_map = {
            "daily_vibe": daily_vibe_prompt,
            "life_advice": life_advice_prompt,
            "mood_checkin": mood_checkin_prompt,
            "relationship": relationship_prompt,
            "default": default_prompt,
        }

    def run(self, user_id: str, user_message: str, memory_manager, force_type=None):
        if len(user_message.split()) < 3 or user_message.lower() in ["ok", "hmm", "idk", "lol", "k", "whatever"]:
            return get_tiny_reply(user_message)

        message_type = force_type or classify_message(user_message)

        # Pick prompt
        prompt_template = self.prompt_map.get(message_type, default_prompt)

        # Retrieve past memory (tiny convo history)
        past_memory = memory_manager.get_memory(user_id)
        memory_text = "\n".join([f"{m['role'].capitalize()}: {m['text']}" for m in past_memory])

        # Format prompt
        full_input = f"Previous conversation:\n{memory_text}\n\nNew message:\n{user_message}"

        chain = LLMChain(llm=self.llm, prompt=prompt_template)
        response = chain.invoke({"user_message": full_input})

        # Update memory
        emotion_tone = detect_emotion_tone(user_message)
        memory_manager.add_message(user_id, "user", {"text": user_message, "tone": emotion_tone})
        memory_manager.add_message(user_id, "ai", {"text": response['text'], "tone": "neutral"})

        return response['text']

def get_tiny_reply():
    tiny_replies = [
        "🌸 Got you. Wanna talk about what's on your mind?",
        "😌 No rush, just here whenever you wanna chat.",
        "💬 Sometimes even a 'hmm' says a lot, y'know?",
        "✨ I'm listening even to the little pauses.",
        "🫶 Totally okay to just be here. No pressure.",
        "🌷 Soft moments matter too. What's pulling on your heart today?",
        "💖 I'm holding space for you, even in the silence.",
    ]
    return random.choice(tiny_replies)

def detect_emotion_tone(text):
    text = text.lower()
    if any(word in text for word in ["sad", "upset", "hurt", "heartbroken", "lonely"]):
        return "sad"
    if any(word in text for word in ["excited", "happy", "joy", "grateful"]):
        return "happy"
    if any(word in text for word in ["confused", "lost", "overwhelmed"]):
        return "confused"
    if any(word in text for word in ["tired", "exhausted", "drained"]):
        return "tired"
    return "neutral"