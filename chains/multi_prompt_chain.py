from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

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
        memory_manager.add_message(user_id, "user", user_message)
        memory_manager.add_message(user_id, "ai", response['text'])

        return response['text']
