"""
T-102: OpenAI implementation of LLM Client
"""
import os
import json
import logging
import time
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from openai import OpenAI, APIError, APITimeoutError, RateLimitError as OpenAIRateLimitError

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
from .models import LLMRequest, LLMJsonRequest, LLMResponse, LLMUsage, LLMMessage

logger = logging.getLogger(__name__)

# --- JSON Schema Validation (T-102.3) ---

try:
    from jsonschema import validate, ValidationError as JSONSchemaValidationError
    HAS_JSONSCHEMA =True
except ImportError:
    HAS_JSONSCHEMA = False
    JSONSchemaValidationError = None

def validate_json_schema(data: dict, schema: dict):
    """
    Validate JSON data against schema.
    
    Raises:
        LLMJsonSchemaViolationError if validation fails
    """
    if not HAS_JSONSCHEMA:
        # Fallback: basic validation
        if "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    raise LLMJsonSchemaViolationError(f"Missing required field: {field}")
        return
    
    try:
        validate(instance=data, schema=schema)
    except JSONSchemaValidationError as e:
        raise LLMJsonSchemaViolationError(f"Schema validation failed: {e.message}")

# --- OpenAI Client Implementation (T-102.6) ---

class OpenAIClient(LLMClient):
    """
    OpenAI implementation of LLMClient.
    Handles retries, rate limiting, and error translation.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_timeout_s: float = 60.0,
        max_retries: int = 3
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Custom base URL (optional)
            default_timeout_s: Default timeout for requests
            max_retries: Max retry attempts for rate limits/transient errors
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY not found in environment or constructor")
        
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.default_timeout_s = default_timeout_s
        self.max_retries = max_retries
        
        # Initialize OpenAI SDK client
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        self.client = OpenAI(**client_kwargs)
    
    def _build_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage to OpenAI format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    @retry(
        retry=retry_if_exception_type((OpenAIRateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_openai(self, req: LLMRequest, response_format: Optional[dict] = None) -> dict:
        """
        Internal method to call OpenAI API with retries.
        
        Args:
            req: LLM request
            response_format: Optional response format (for JSON mode)
            
        Returns:
            Raw API response
            
        Raises:
            LLMTimeoutError, LLMRateLimitError, LLMProviderError
        """
        messages = self._build_messages(req.messages)
        
        kwargs = {
            "model": req.model,
            "messages": messages,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "timeout": req.timeout_s or self.default_timeout_s
        }
        
        if req.top_p is not None:
            kwargs["top_p"] = req.top_p
        if req.seed is not None:
            kwargs["seed"] = req.seed
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            start_time = time.time()
            response = self.client.chat.completions.create(**kwargs)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log trace info (T-102.5)
            logger.info(
                f"LLM Request | run_id={req.run_id} step={req.step_name} beat={req.beat_id} "
                f"model={req.model} latency={latency_ms}ms tokens={response.usage.total_tokens if response.usage else 0}"
            )
            
            return {
                "response": response,
                "latency_ms": latency_ms
            }
            
        except APITimeoutError as e:
            logger.error(f"LLM Timeout: {e}")
            raise LLMTimeoutError(f"Request timed out: {e}")
        except OpenAIRateLimitError as e:
            logger.warning(f"LLM Rate Limit: {e}")
            raise LLMRateLimitError(f"Rate limit hit: {e}")
        except APIError as e:
            logger.error(f"LLM Provider Error: {e}")
            raise LLMProviderError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"LLM Unexpected Error: {e}")
            raise LLMError(f"Unexpected error: {e}")
    
    def generate_text(self, req: LLMRequest) -> LLMResponse:
        """Generate free-form text response"""
        result = self._call_openai(req)
        response = result["response"]
        choice = response.choices[0]
        
        usage = None
        if response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
        
        return LLMResponse(
            text=choice.message.content or "",
            usage=usage,
            request_id=response.id,
            provider="openai",
            model=response.model,
            latency_ms=result["latency_ms"],
            raw=response.model_dump()
        )
    
    def generate_json(self, req: LLMJsonRequest) -> LLMResponse:
        """
        Generate JSON response with schema validation.
        
        Raises:
            LLMInvalidSchemaError if schema is missing
            LLMJsonParseError if response isn't valid JSON
            LLMJsonSchemaViolationError if JSON doesn't match schema
        """
        # Validate schema presence (T-102.3)
        if not req.json_schema:
            raise LLMInvalidSchemaError("json_schema is required for generate_json")
        
        # Request JSON mode from OpenAI
        response_format = {"type": "json_object"}
        
        result = self._call_openai(req, response_format=response_format)
        response = result["response"]
        choice = response.choices[0]
        
        text = choice.message.content or "{}"
        
        # Parse JSON (T-102.3)
        try:
            json_data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            raise LLMJsonParseError(f"Failed to parse JSON: {e}")
        
        # Validate against schema (T-102.3)
        try:
            validate_json_schema(json_data, req.json_schema)
        except LLMJsonSchemaViolationError:
            logger.error(f"Schema Violation: {json_data}")
            raise
        
        usage = None
        if response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
        
        return LLMResponse(
            text=text,
            json=json_data,
            usage=usage,
            request_id=response.id,
            provider="openai",
            model=response.model,
            latency_ms=result["latency_ms"],
            raw=response.model_dump()
        )
