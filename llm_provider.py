# llm_provider.py
import os
from typing import Dict, Tuple, Union
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

# Load .env exactly once here
load_dotenv()

# Determine which provider to use
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()  # Default to Gemini

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

# Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite").strip()

# Optional default temperature override via .env
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Cache LLM instances by (provider, model, temperature)
_clients: Dict[Tuple[str, str, float], Union[ChatGroq, ChatGoogleGenerativeAI]] = {}

def get_llm_client(temperature: float | None = None, provider: str | None = None) -> Union[ChatGroq, ChatGoogleGenerativeAI]:
    """
    Returns a cached LLM instance (Groq or Gemini) based on configuration.
    - temperature: if None, uses DEFAULT_TEMPERATURE from env.
    - provider: if None, uses LLM_PROVIDER from env.
    """
    temp = DEFAULT_TEMPERATURE if temperature is None else float(temperature)
    prov = LLM_PROVIDER if provider is None else provider.lower()
    
    if prov == "groq":
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not set in environment (.env).")
        key = ("groq", GROQ_MODEL, temp)
        if key not in _clients:
            _clients[key] = ChatGroq(
                model_name=GROQ_MODEL,
                temperature=temp,
                groq_api_key=GROQ_API_KEY,
            )
    elif prov == "gemini":
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY not set in environment (.env).")
        key = ("gemini", GEMINI_MODEL, temp)
        if key not in _clients:
            _clients[key] = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                temperature=temp,
                google_api_key=GOOGLE_API_KEY,
            )
    else:
        raise ValueError(f"Unsupported LLM provider: {prov}. Use 'groq' or 'gemini'.")
    
    return _clients[key]

# Backward compatibility function
def get_chat_groq(temperature: float | None = None) -> Union[ChatGroq, ChatGoogleGenerativeAI]:
    """
    Backward compatibility wrapper. Now returns the configured LLM provider.
    """
    return get_llm_client(temperature=temperature)
