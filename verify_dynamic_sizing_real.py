
import sys
import os
from pathlib import Path

# Add src to python path
sys.path.append(os.getcwd())

from src.agents.beat_segmenter import BeatSegmenterAgent
from src.llm import MockLLMClient

def verify_real_data_sizing():
    script_path = Path("inputs_test/valid_script.txt")
    print(f"--- Verifying Dynamic Sizing with Real Data ---")
    print(f"Target File: {script_path}")
    
    if not script_path.exists():
        print(f"[ERROR] File not found: {script_path}")
        return

    # Read real script
    with open(script_path, 'r') as f:
        script_text = f.read()
        
    # Init agent (Mock LLM is fine, we are testing the math logic in __init__/_calculate)
    agent = BeatSegmenterAgent(MockLLMClient({}))
    
    print(f"\n[ANALYSIS]")
    # Calculate directly
    min_b, max_b = agent._calculate_dynamic_limits(script_text)
    
    # Text stats for context
    words = len(script_text.split())
    approx_duration = words / 2.8
    
    print(f"  Word Count: {words}")
    print(f"  Est. Duration: {approx_duration:.1f} seconds (~{approx_duration/60:.1f} minutes)")
    print(f"  Target Beat Duration: {agent.target_beat_duration}s (Configured)")
    
    print(f"\n[RESULT]")
    print(f"  Old Constraints: Min=6, Max=18 (Hardcoded)")
    print(f"  New Dynamic Constraints: Min={min_b}, Max={max_b}")
    
    print(f"\n[CONCLUSION]")
    if max_b > 20:
        print(f"  SUCCESS: The agent now permits up to {max_b} beats, solving the 'only 20 beats' limitation.")
    else:
        print(f"  FAIL: The agent is still restricting beat count too aggressively.")

if __name__ == "__main__":
    verify_real_data_sizing()
