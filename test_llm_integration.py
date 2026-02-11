"""
Quick integration test for T-102 LLM Client
"""
import os
from dotenv import load_dotenv

load_dotenv()

from src.llm import (
    MockLLMClient,
    LLMRequest,
    LLMMessage,
    build_llm_client
)

def test_mock_client_integration():
    """Verify MockLLMClient works as expected"""
    
    # Create fixtures
    fixtures = {
        "test_hash": {
            "text": "This is a test response from the mock client"
        }
    }
    
    # Build client via factory
    client = build_llm_client("mock", fixtures=fixtures)
    
    # Override hash for testing
    client._compute_request_hash = lambda req, include_schema=False: "test_hash"
    
    # Create request
    req = LLMRequest(
        messages=[
            LLMMessage(role="system", content="Test system"),
            LLMMessage(role="user", content="Test user message")
        ],
        model="test-model",
        run_id="TEST_RUN",
        step_name="INTEGRATION_TEST"
    )
    
    # Generate
    response = client.generate_text(req)
    
    # Verify
    assert response.text == "This is a test response from the mock client"
    assert response.provider == "mock"
    assert response.model == "test-model"
    assert len(client.call_log) == 1
    assert client.call_log[0]["run_id"] == "TEST_RUN"
    
    print("✅ Mock client integration test passed!")
    return True

if __name__ == "__main__":
    test_mock_client_integration()
    print("\n🎉 T-102 LLM Client is ready for use!")
