#!/usr/bin/env python3
"""
T-102 Demo: Test LLM Client with real OpenAI API
"""
import os
import sys
from dotenv import load_dotenv

# Load .env
load_dotenv()

from src.llm import (
    OpenAIClient,
    LLMRequest,
    LLMMessage,
    LLMJsonRequest,
    LLMError
)

def demo_text_generation():
    """Demo: Simple text generation"""
    print("=" * 60)
    print("DEMO 1: Text Generation")
    print("=" * 60)
    
    client = OpenAIClient()
    
    req = LLMRequest(
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Say hello in Spanish.")
        ],
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=50,
        run_id="DEMO_RUN",
        step_name="TEXT_DEMO"
    )
    
    try:
        response = client.generate_text(req)
        print(f"\n✅ Response: {response.text}")
        print(f"📊 Usage: {response.usage.total_tokens} tokens")
        print(f"⏱️  Latency: {response.latency_ms}ms")
        print(f"🔑 Request ID: {response.request_id}")
    except LLMError as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True

def demo_json_generation():
    """Demo: JSON generation with schema validation"""
    print("\n" + "=" * 60)
    print("DEMO 2: JSON Generation with Schema")
    print("=" * 60)
    
    client = OpenAIClient()
    
    schema = {
        "type": "object",
        "properties": {
            "greeting": {"type": "string"},
            "language": {"type": "string"},
            "enthusiasm_level": {"type": "integer", "minimum": 1, "maximum": 10}
        },
        "required": ["greeting", "language"]
    }
    
    req = LLMJsonRequest(
        messages=[
            LLMMessage(
                role="system", 
                content="You respond with JSON only. Generate a greeting object."
            ),
            LLMMessage(
                role="user", 
                content="Generate a Spanish greeting with high enthusiasm."
            )
        ],
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=100,
        json_schema=schema,
        run_id="DEMO_RUN",
        step_name="JSON_DEMO"
    )
    
    try:
        response = client.generate_json(req)
        print(f"\n✅ JSON Response:")
        import json
        print(json.dumps(response.json, indent=2))
        print(f"\n📊 Usage: {response.usage.total_tokens} tokens")
        print(f"⏱️  Latency: {response.latency_ms}ms")
    except LLMError as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True

def main():
    """Run all demos"""
    print("\n🚀 T-102 LLM Client Demo")
    print("Using OpenAI API from .env\n")
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Make sure .env file is present and contains OPENAI_API_KEY")
        sys.exit(1)
    
    print(f"✅ API Key found: {os.getenv('OPENAI_API_KEY')[:20]}...")
    
    # Run demos
    success = True
    
    if not demo_text_generation():
        success = False
    
    if not demo_json_generation():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All demos completed successfully!")
        print("T-102 LLM Client is working correctly with OpenAI API")
    else:
        print("❌ Some demos failed")
    print("=" * 60 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
