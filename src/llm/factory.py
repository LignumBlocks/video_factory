"""
T-102: LLM Client Factory for provider routing
"""
import os
from typing import Dict, Any, Optional

from .client import LLMClient, LLMError
from .openai_client import OpenAIClient
from .mock_client import MockLLMClient

def build_llm_client(
    provider: str,
    settings: Optional[Dict[str, Any]] = None,
    fixtures: Optional[Dict[str, Any]] = None
) -> LLMClient:
    """
    Build LLM client based on provider name (T-102.8).
    
    Args:
        provider: Provider name ("openai", "mock")
        settings: Provider-specific settings (api_key, timeout, etc.)
        fixtures: For mock provider only, fixture dictionary
        
    Returns:
        Configured LLMClient instance
        
    Raises:
        LLMError if provider unknown or config invalid
    """
    settings = settings or {}
    
    if provider == "openai":
        return OpenAIClient(
            api_key=settings.get("api_key"),
            base_url=settings.get("base_url"),
            default_timeout_s=settings.get("timeout_s", 60.0),
            max_retries=settings.get("max_retries", 3)
        )
    
    elif provider == "mock":
        if fixtures is None:
            raise LLMError("Mock provider requires 'fixtures' argument")
        return MockLLMClient(fixtures=fixtures)
    
    else:
        raise LLMError(f"Unknown LLM provider: {provider}")

def build_llm_client_from_config(config_dict: Dict[str, Any]) -> LLMClient:
    """
    Build client from agent_settings config (from system_rules.yaml).
    
    Example config_dict:
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 1200
    }
    
    Args:
        config_dict: Agent settings from system rules
        
    Returns:
        Configured LLMClient
    """
    provider = config_dict.get("provider", "openai")
    
    settings = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "timeout_s": config_dict.get("timeout_s", 60.0),
        "max_retries": config_dict.get("max_retries", 3)
    }
    
    return build_llm_client(provider, settings)
