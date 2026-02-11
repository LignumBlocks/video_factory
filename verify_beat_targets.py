
from pathlib import Path
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.agents.beat_segmenter import BeatSegmenterAgent
from src.llm import MockLLMClient

def verify_targets():
    script_path = Path("inputs_test/valid_script.txt")
    if not script_path.exists():
        print(f"Error: {script_path} not found.")
        return

    script_text = script_path.read_text()
    
    agent = BeatSegmenterAgent(MockLLMClient({}))
    
    # Check word count
    # clean slightly to match agent logic
    words = len(script_text.split())
    
    print(f"--- Dynamic Beat Sizing Verification ---")
    print(f"Input Script: {script_path}")
    print(f"Word Count: {words}")
    
    # Calculate limits
    min_b, max_b = agent._calculate_dynamic_limits(script_text)
    
    print(f"Calculated Limits:")
    print(f"  Min Beats: {min_b}")
    print(f"  Max Beats: {max_b}")
    
    print(f"\nConfiguration:")
    print(f"  Target Duration: {agent.target_beat_duration}s")
    print(f"  Words Per Sec: 2.8")

if __name__ == "__main__":
    verify_targets()
