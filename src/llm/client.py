"""
T-102: LLM Client base interface and exceptions
"""
from abc import ABC, abstractmethod
from .models import LLMRequest, LLMJsonRequest, LLMResponse

# --- Typed Exceptions (T-102.4) ---

class LLMError(Exception):
    """Base exception for all LLM errors"""
    pass

class LLMTimeoutError(LLMError):
    """Request timed out"""
    pass

class LLMRateLimitError(LLMError):
    """Provider rate limit exceeded"""
    pass

class LLMProviderError(LLMError):
    """Provider returned an error"""
    pass

class LLMInvalidSchemaError(LLMError):
    """JSON schema is invalid or missing"""
    pass

class LLMJsonParseError(LLMError):
    """Failed to parse JSON from response"""
    pass

class LLMJsonSchemaViolationError(LLMError):
    """Response JSON doesn't match required schema"""
    pass

# --- Base Client Interface (T-102.2) ---

class LLMClient(ABC):
    """
    Abstract base for all LLM clients.
    Agents must ONLY use this interface, never import provider SDKs directly.
    """
    
    @abstractmethod
    def generate_text(self, req: LLMRequest) -> LLMResponse:
        """
        Generate free-form text response.
        
        Args:
            req: Request with messages and parameters
            
        Returns:
            LLMResponse with text field populated
            
        Raises:
            LLMError subclasses on failure
        """
        ...
    
    @abstractmethod
    def generate_json(self, req: LLMJsonRequest) -> LLMResponse:
        """
        Generate JSON-structured response validated against schema.
        
        Args:
            req: Request with json_schema (required)
            
        Returns:
            LLMResponse with both text and json fields populated
            
        Raises:
            LLMInvalidSchemaError: if json_schema is missing/invalid
            LLMJsonParseError: if response isn't valid JSON
            LLMJsonSchemaViolationError: if JSON doesn't match schema
            Other LLMError subclasses on provider/network failures
        """
        ...
