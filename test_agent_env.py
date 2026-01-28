import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env
load_dotenv()

from src.clients.agent import AgentClient

def test_agent():
    print("Testing Agent Client with dotenv...")
    
    agent_key = os.environ.get("AGENT_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("AGENT_MODEL")
    
    print(f"AGENT_API_KEY present: {bool(agent_key)}")
    print(f"GEMINI_API_KEY present: {bool(gemini_key)}")
    print(f"Model from ENV: {model}")
    
    client = AgentClient()
    print(f"Client effective Model: {client.model}")
    
    print("Attempting suggest_visuals call...")
    try:
        # Simple test prompt
        result = client.suggest_visuals("A chart showing exponential growth over time.")
        if result:
            print("SUCCESS. Result:")
            print(result)
        else:
            print("FAILURE. Result is None (Fallback triggered or API Error)")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_agent()
