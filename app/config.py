import os
from dotenv import load_dotenv

load_dotenv()

# Gemini API Configuration (Google AI Studio)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Request timeout for LLM calls (seconds)
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
