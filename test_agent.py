import os
import sys

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.clients.agent import AgentClient

def test_agent():
    print("Testing Agent Client...")
    
    # Check env vars (safe print)
    agent_key = os.environ.get("AGENT_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    print(f"AGENT_API_KEY present: {bool(agent_key)}")
    print(f"GEMINI_API_KEY present: {bool(gemini_key)}")
    
    client = AgentClient()
    print(f"Client Model: {client.model}")
    print(f"Client Base URL: {client.base_url}")
    
    print("Attempting suggest_visuals call...")
    try:
        result = client.suggest_visuals("A chart showing exponential growth over time.")
        if result:
            print("SUCCESS. Result:")
            print(result)
        else:
            print("FAILURE. Result is None (Fallback triggered)")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_agent()
