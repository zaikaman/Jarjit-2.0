from typing import List
import os
from threading import Lock
from dotenv import load_dotenv
import json

class APIKeyManager:
    def __init__(self):
        load_dotenv()
        self.api_keys = self._load_api_keys()
        self.current_index = 0
        self._lock = Lock()
        self.rate_limited_keys = set()
        self.rate_limited_file = "rate_limited_keys.txt"
        self._load_rate_limited_keys()
    
    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment variables"""
        keys_str = os.getenv('GITHUB_API_KEYS', '[]')
        try:
            keys = json.loads(keys_str)
            if not keys or not isinstance(keys, list):
                raise ValueError("API keys must be a non-empty array")
            return keys
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for API keys in environment variable")
        
    def _load_rate_limited_keys(self):
        """Load previously rate-limited keys from file if it exists"""
        if os.path.exists(self.rate_limited_file):
            with open(self.rate_limited_file, 'r') as f:
                self.rate_limited_keys = set(line.strip() for line in f.readlines())
                
    def mark_key_rate_limited(self, key: str):
        """Mark a key as rate-limited and save it to file"""
        with self._lock:
            self.rate_limited_keys.add(key)
            with open(self.rate_limited_file, 'a') as f:
                f.write(f"{key}\n")
        
    def get_next_key(self) -> str:
        """Get next available non-rate-limited key"""
        with self._lock:
            attempts = 0
            while attempts < len(self.api_keys):
                key = self.api_keys[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.api_keys)
                if key not in self.rate_limited_keys:
                    return key
                attempts += 1
            raise Exception("All API keys are rate-limited")

# Initialize global API key manager
api_key_manager = APIKeyManager()

# Azure OpenAI configuration
AZURE_OPENAI_BASE_URL = os.getenv('AZURE_OPENAI_BASE_URL', "https://models.inference.ai.azure.com")
AZURE_OPENAI_MODEL = os.getenv('AZURE_OPENAI_MODEL', "gpt-4o")
