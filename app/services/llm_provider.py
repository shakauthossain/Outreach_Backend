"""LLM provider abstraction supporting Groq and Google Gemini."""

import os
from typing import Dict, Tuple, Union, Optional
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings


class LLMProvider:
    """LLM provider with caching and support for multiple backends."""
    
    def __init__(self):
        self._clients: Dict[Tuple[str, str, float], Union[ChatGroq, ChatGoogleGenerativeAI]] = {}
        self.provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite").strip()
        self.default_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    def get_client(
        self, 
        temperature: Optional[float] = None, 
        provider: Optional[str] = None
    ) -> Union[ChatGroq, ChatGoogleGenerativeAI]:
        """
        Get a cached LLM client instance.
        
        Args:
            temperature: Model temperature (0.0-1.0). Uses default if None.
            provider: "groq" or "gemini". Uses configured provider if None.
            
        Returns:
            Configured LLM client instance
            
        Raises:
            RuntimeError: If API key is not configured
            ValueError: If provider is not supported
        """
        temp = self.default_temperature if temperature is None else float(temperature)
        prov = self.provider if provider is None else provider.lower()
        
        if prov == "groq":
            if not self.groq_api_key:
                raise RuntimeError("GROQ_API_KEY not set in environment")
            
            key = ("groq", self.groq_model, temp)
            if key not in self._clients:
                self._clients[key] = ChatGroq(
                    model_name=self.groq_model,
                    temperature=temp,
                    groq_api_key=self.groq_api_key,
                )
            return self._clients[key]
            
        elif prov == "gemini":
            if not self.google_api_key:
                raise RuntimeError("GOOGLE_API_KEY not set in environment")
            
            key = ("gemini", self.gemini_model, temp)
            if key not in self._clients:
                self._clients[key] = ChatGoogleGenerativeAI(
                    model=self.gemini_model,
                    temperature=temp,
                    google_api_key=self.google_api_key,
                )
            return self._clients[key]
            
        else:
            raise ValueError(f"Unsupported LLM provider: {prov}. Use 'groq' or 'gemini'")
    
    def clear_cache(self):
        """Clear all cached LLM clients."""
        self._clients.clear()


# Global instance
llm_provider = LLMProvider()


def get_llm_client(
    temperature: Optional[float] = None, 
    provider: Optional[str] = None
) -> Union[ChatGroq, ChatGoogleGenerativeAI]:
    """
    Convenience function to get LLM client from global provider.
    
    Args:
        temperature: Model temperature (0.0-1.0)
        provider: "groq" or "gemini"
        
    Returns:
        Configured LLM client instance
    """
    return llm_provider.get_client(temperature=temperature, provider=provider)
