"""
T-102: LLM Client Package
Unified interface for LLM interactions across all agents.
"""
from .models import LLMMessage, LLMRequest, LLMJsonRequest, LLMResponse, LLMUsage
from .client import (
    LLMClient,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMProviderError,
    LLMInvalidSchemaError,
    LLMJsonParseError,
    LLMJsonSchemaViolationError
)
from .openai_client import OpenAIClient
from .mock_client import MockLLMClient, MissingFixtureError
from .factory import build_llm_client, build_llm_client_from_config

__all__ = [
    # Models
    "LLMMessage",
    "LLMRequest",
    "LLMJsonRequest",
    "LLMResponse",
    "LLMUsage",
    
    # Base Client
    "LLMClient",
    
    # Exceptions
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMProviderError",
    "LLMInvalidSchemaError",
    "LLMJsonParseError",
    "LLMJsonSchemaViolationError",
    "MissingFixtureError",
    
    # Implementations
    "OpenAIClient",
    "MockLLMClient",
    
    # Factory
    "build_llm_client",
    "build_llm_client_from_config"
]
