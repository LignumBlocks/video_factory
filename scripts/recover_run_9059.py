import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.orchestrator import RunOrchestrator
from src.foundation.manifest import Phase

RUN_ID = "RUN-9059"
STAGING_DIR = "runs/RUN-9059/v1/staging"
SCRIPT = os.path.join(STAGING_DIR, "script.txt")
AUDIO = os.path.join(STAGING_DIR, "voiceover.mp3")
BIBLE = os.path.join(STAGING_DIR, "style_bible.md")

def recover():
    print(f"Recovering {RUN_ID} to V1 System...")
    
    if os.path.exists(f"artifacts/{RUN_ID}/run_manifest.json"):
        print("Removing legacy manifest...")
        os.remove(f"artifacts/{RUN_ID}/run_manifest.json")
        
    orch = RunOrchestrator(run_id=RUN_ID)
    
    # 1. Initialize (Overwrite legacy manifest)
    print("Step 1: Initialize (Ingest)")
    orch.initialize_run(SCRIPT, AUDIO, BIBLE)
    
    # 2. Planning
    print("Step 2: Execute Planning")
    orch.execute_stage("planning")
    
    print("Recovery Complete. Check artifacts/RUN-9059/run_manifest.json")

if __name__ == "__main__":
    recover()
