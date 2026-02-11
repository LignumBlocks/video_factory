# LLM Client Guide - T-102

## Overview

El sistema LLM Client proporciona una interfaz unificada para interactuar con modelos de lenguaje, desacoplando completamente los agentes del proveedor específico (OpenAI, etc.).

## Configuration

### Environment Variables (.env)

```bash
# OpenAI API Key (required for production)
OPENAI_API_KEY=sk-proj-...

# Optional: Custom base URL
OPENAI_BASE_URL=https://api.openai.com/v1
```

## Quick Start

### 1. Text Generation (Simple)

```python
from src.llm import OpenAIClient, LLMRequest, LLMMessage

# Create client
client = OpenAIClient()

# Create request
req = LLMRequest(
    messages=[
        LLMMessage(role="system", content="You are a helpful assistant"),
        LLMMessage(role="user", content="Explain quantum computing in 2 sentences")
    ],
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=100,
    
    # Optional: Tracing metadata
    run_id="RUN_123",
    step_name="EXPLANATION",
    beat_id="B001"
)

# Generate
response = client.generate_text(req)
print(response.text)
print(f"Tokens used: {response.usage.total_tokens}")
```

### 2. JSON Generation (Structured)

```python
from src.llm import OpenAIClient, LLMJsonRequest, LLMMessage

client = OpenAIClient()

# Define schema
schema = {
    "type": "object",
    "properties": {
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "action": {"type": "string"},
                    "intensity": {"type": "string", "enum": ["low", "med", "high"]}
                },
                "required": ["id", "action"]
            }
        }
    },
    "required": ["beats"]
}

req = LLMJsonRequest(
    messages=[
        LLMMessage(role="system", content="Generate beat structure as JSON"),
        LLMMessage(role="user", content="Create 3 beats for a finance video")
    ],
    model="gpt-4o-mini",
    json_schema=schema,
    run_id="RUN_456"
)

response = client.generate_json(req)
beats = response.json["beats"]  # Already validated!
```

## Agent Integration (T-102.9)

### Dependency Injection Pattern

```python
from src.llm import LLMClient, LLMRequest, LLMMessage

class BeatSegmenterAgent:
    """Example agent using LLM client"""
    
    def __init__(self, llm: LLMClient):
        self.llm = llm  # NO direct SDK imports!
    
    def segment_beats(self, script: str, run_id: str) -> list:
        req = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content="Segment script into narrative beats"
                ),
                LLMMessage(role="user", content=script)
            ],
            model="gpt-4o-mini",
            temperature=0.2,
            run_id=run_id,
            step_name="BEAT_SEGMENTATION"
        )
        
        response = self.llm.generate_text(req)
        return self._parse_beats(response.text)
```

### Production Usage

```python
from src.llm import build_llm_client_from_config

# Load from system_rules.yaml -> agent_settings.beat_segmenter
config = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "max_tokens": 1200
}

llm = build_llm_client_from_config(config)
agent = BeatSegmenterAgent(llm=llm)
```

### Test Usage (Deterministic)

```python
from src.llm import MockLLMClient

# Define fixtures
fixtures = {
    "abc123": {  # Hash of request
        "text": "Beat 1: Introduction\nBeat 2: Rising action\nBeat 3: Climax"
    }
}

mock_llm = MockLLMClient(fixtures=fixtures)
agent = BeatSegmenterAgent(llm=mock_llm)

# Test runs deterministically!
result = agent.segment_beats("Script...", "TEST_RUN")
```

## Error Handling

```python
from src.llm import (
    LLMTimeoutError,
    LLMRateLimitError,
    LLMJsonSchemaViolationError,
    LLMError
)

try:
    response = client.generate_json(req)
except LLMTimeoutError:
    logger.error("Request timed out, retry with longer timeout")
except LLMRateLimitError:
    logger.warning("Rate limit hit, backoff handled automatically")
except LLMJsonSchemaViolationError as e:
    logger.error(f"LLM output doesn't match schema: {e}")
except LLMError as e:
    logger.error(f"LLM error: {e}")
```

## Retry Behavior (Automatic)

El cliente maneja automáticamente:
- ✅ **Rate limits**: 3 retries con exponential backoff
- ✅ **Transient errors**: 3 retries
- ✅ **Timeouts**: 1 retry
- ❌ **Schema violations**: NO retry (error del agente)
- ❌ **Invalid schema**: NO retry (error de configuración)

## Logging & Tracing

Todos los requests se loggean automáticamente:

```
INFO - LLM Request | run_id=RUN_123 step=BEAT_SEGMENTATION beat=B001 
       model=gpt-4o-mini latency=342ms tokens=156
```

Metadata incluida:
- `run_id`, `step_name`, `beat_id` (si se proveen)
- `model`, `provider`
- `latency_ms`
- `usage` (tokens)
- `request_id` (del proveedor)

## Testing Best Practices

### 1. Use MockLLMClient for unit tests

```python
def test_agent_logic():
    """Test agent logic without network calls"""
    fixtures = {"hash1": {"text": "Expected output"}}
    mock_llm = MockLLMClient(fixtures)
    
    agent = MyAgent(llm=mock_llm)
    result = agent.process()
    
    # Assert on result
    assert result == expected
    
    # Assert on LLM calls
    assert len(mock_llm.call_log) == 1
    assert mock_llm.call_log[0]["step_name"] == "PROCESSING"
```

### 2. Compute hashes for fixtures

```python
from src.llm.mock_client import MockLLMClient

client = MockLLMClient({})
req = LLMRequest(messages=[...], model="gpt-4o-mini")

# Compute hash
hash_val = client._compute_request_hash(req)
print(f"Use this hash in fixtures: {hash_val}")
```

### 3. Integration tests with real API (optional)

```python
@pytest.mark.integration
def test_real_openai():
    """Integration test with real API (skipped in CI)"""
    client = OpenAIClient()
    req = LLMRequest(...)
    response = client.generate_text(req)
    assert response.text is not None
```

## Factory Pattern

```python
from src.llm import build_llm_client

# For production
llm = build_llm_client("openai", settings={
    "api_key": "sk-...",
    "timeout_s": 120,
    "max_retries": 5
})

# For tests
llm = build_llm_client("mock", fixtures={...})
```

## Rules & Constraints (T-102)

### ❌ Prohibited

- Agents **CANNOT** import `openai` SDK directly
- Agents **CANNOT** make HTTP requests directly
- Agents **CANNOT** handle retries manually

### ✅ Required

- Agents **MUST** accept `LLMClient` via constructor
- Agents **MUST** use only `generate_text` or `generate_json`
- JSON generation **MUST** include `json_schema`

## Demo

Run the included demo to verify setup:

```bash
./demo_llm_client.py
```

This will test both text and JSON generation with your OpenAI API key.
