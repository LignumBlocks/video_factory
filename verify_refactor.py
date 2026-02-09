import os
import sys
from dotenv import load_dotenv
load_dotenv("/home/roiky/Espacio/FinanceVideoPlatform/.env")
from src.orchestrator import RunOrchestrator

def verify_pipeline():
    # Setup
    run_id = "RUN-STRICT"
    video_id = "VID_TEST"
    
    # Inputs (from RUN-7066)
    base_input = "/home/roiky/Espacio/FinanceVideoPlatform/artifacts/RUN-7066/inputs"
    script = os.path.join(base_input, "script.txt")
    audio = os.path.join(base_input, "voiceover.mp3")
    bible = os.path.join(base_input, "bible.md")
    
    print(f"--- Starting Strict Verification for {run_id} ---")
    
    try:
        orchestrator = RunOrchestrator(run_id=run_id, video_id=video_id)
        
        # 1. Initialize (Ingest)
        print("\n[1] Running INGEST...")
        orchestrator.initialize_run(script, audio, bible)
        
        # 2. Planning
        print("\n[2] Running PLANNING...")
        orchestrator.execute_stage("planning")
        
        # 3. Prompts
        print("\n[3] Running PROMPTS...")
        orchestrator.execute_stage("prompts")
        
        print("\n--- Verification DONE: Success ---")
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_pipeline()
