from typing import List
import os
from threading import Lock

class APIKeyManager:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_index = 0
        self._lock = Lock()
        
    def get_next_key(self) -> str:
        with self._lock:
            key = self.api_keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            return key

# Initialize global API key manager
CHAT_API_KEYS = [
    
]

api_key_manager = APIKeyManager(CHAT_API_KEYS)

# Azure OpenAI configuration
AZURE_OPENAI_BASE_URL = "https://models.inference.ai.azure.com"
AZURE_OPENAI_MODEL = "gpt-4o"
