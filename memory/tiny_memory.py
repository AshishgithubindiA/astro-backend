from collections import defaultdict, deque

class TinyMemory:
    def __init__(self, max_memory: int = 5):
        self.memory = defaultdict(lambda: deque(maxlen=max_memory))

    def add_message(self, user_id: str, role: str, text: str):
        self.memory[user_id].append({"role": role, "text": text})

    def get_memory(self, user_id: str):
        return list(self.memory[user_id])

    def clear_memory(self, user_id: str):
        self.memory.pop(user_id, None)
