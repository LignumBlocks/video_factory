"""
T-102: LLM Client data models and contracts
"""
from dataclasses import dataclass, field
from typing import Literal, Optional, Any, Dict, List

# Role type for LLM messages
Role = Literal["system", "user", "assistant"]

@dataclass
class LLMMessage:
    """Single message in a conversation"""
    role: Role
    content: str

@dataclass
class LLMUsage:
    """Token usage statistics"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class LLMRequest:
    """Base request for LLM generation"""
    messages: List[LLMMessage]
    model: str
    temperature: float = 0.2
    max_tokens: int = 1200
    top_p: Optional[float] = None
    seed: Optional[int] = None
    timeout_s: float = 60.0
    
    # Metadata for tracing (not sent to model unless provider allows)
    run_id: Optional[str] = None
    step_name: Optional[str] = None
    beat_id: Optional[str] = None
    tags: Optional[Dict[str, str]] = field(default_factory=dict)

@dataclass
class LLMJsonRequest(LLMRequest):
    """Request for JSON-structured generation with schema validation"""
    json_schema: Optional[Dict[str, Any]] = None

@dataclass
class LLMResponse:
    """Standard LLM response"""
    text: str
    json: Optional[Dict[str, Any]] = None  # For generate_json
    usage: Optional[LLMUsage] = None
    request_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None  # Original provider response
