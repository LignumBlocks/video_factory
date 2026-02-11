"""
T-102: Mock LLM Client for deterministic testing
"""
import hashlib
import json
import logging
from typing import Dict, Any

from .client import LLMClient, LLMError
from .models import LLMRequest, LLMJsonRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

class MockLLMClientError(LLMError):
    """Raised when mock client encounters issues"""
    pass

class MissingFixtureError(MockLLMClientError):
    """Raised when no fixture found for request"""
    pass

class MockLLMClient(LLMClient):
    """
    Mock LLM client for deterministic testing (T-102.7).
    
    Uses fixtures mapped by stable hash of request parameters.
    """
    
    def __init__(self, fixtures: Dict[str, Any]):
        """
        Initialize mock client with fixtures.
        
        Args:
            fixtures: Dict mapping request hashes to responses
                     Format: {hash: {"text": "...", "json": {...}}}
        """
        self.fixtures = fixtures
        self.call_log = []  # Track all calls for test assertions
    
    def _compute_request_hash(self, req: LLMRequest, include_schema: bool = False) -> str:
        """
        Compute stable hash of request for fixture matching.
        
        Hash includes: model + messages + (optional) json_schema
        """
        hash_data = {
            "model": req.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages]
        }
        
        if include_schema and isinstance(req, LLMJsonRequest) and req.json_schema:
            hash_data["json_schema"] = req.json_schema
        
        # Stable JSON dump
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()[:16]
    
    def _get_fixture(self, req_hash: str) -> Dict[str, Any]:
        """
        Get fixture for request hash.
        
        Raises:
            MissingFixtureError if not found
        """
        if req_hash not in self.fixtures:
            raise MissingFixtureError(
                f"No fixture found for hash: {req_hash}. "
                f"Available hashes: {list(self.fixtures.keys())}"
            )
        return self.fixtures[req_hash]
    
    def generate_text(self, req: LLMRequest) -> LLMResponse:
        """Generate text from fixture"""
        req_hash = self._compute_request_hash(req, include_schema=False)
        
        self.call_log.append({
            "type": "generate_text",
            "hash": req_hash,
            "run_id": req.run_id,
            "step_name": req.step_name
        })
        
        fixture = self._get_fixture(req_hash)
        
        return LLMResponse(
            text=fixture.get("text", ""),
            json=fixture.get("json"),
            usage=LLMUsage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            ),
            request_id=f"mock_{req_hash}",
            provider="mock",
            model=req.model,
            latency_ms=0
        )
    
    def generate_json(self, req: LLMJsonRequest) -> LLMResponse:
        """Generate JSON from fixture (no validation bypass - still validates!)"""
        req_hash = self._compute_request_hash(req, include_schema=True)
        
        self.call_log.append({
            "type": "generate_json",
            "hash": req_hash,
            "run_id": req.run_id,
            "step_name": req.step_name
        })
        
        fixture = self._get_fixture(req_hash)
        
        # Note: We return the fixture JSON as-is, but schema validation
        # still happens in real agents if they use it properly
        json_data = fixture.get("json")
        if json_data is None:
            raise MockLLMClientError(f"Fixture {req_hash} missing 'json' field")
        
        text = json.dumps(json_data)
        
        return LLMResponse(
            text=text,
            json=json_data,
            usage=LLMUsage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            ),
            request_id=f"mock_{req_hash}",
            provider="mock",
            model=req.model,
            latency_ms=0
        )
    
    def reset_call_log(self):
        """Clear call log (useful for test isolation)"""
        self.call_log = []
