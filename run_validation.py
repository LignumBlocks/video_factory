
import sys
import os
import shutil
from unittest.mock import patch

# Setup Validation Run
run_id = "VAL_001"
version = 1
base_dir = os.path.dirname(os.path.abspath(__file__))
staging_dir = os.path.join(base_dir, "runs", run_id, f"v{version}", "staging")

# Ensure clean slate
if os.path.exists(staging_dir):
    shutil.rmtree(staging_dir)
os.makedirs(staging_dir, exist_ok=True)

# 1. Inputs: Long Script to force splits
# 12s limit. "This is a long sentence..." needs to be long enough.
# Mock aligner does character proportional. 
# 60s total duration. Text length ~ 100 chars?
# If we have 1 big sentence of 60s, it MUST split into 5 chunks of 12s.
script_content = "This is a very long sentence that is intended to test the beat normalizer logic which should strictly split this into multiple segments because the max duration is set to twelve seconds by default and this text combined with the sixty second duration will definitely exceed that limit significantly."
with open(os.path.join(staging_dir, "script.txt"), "w") as f:
    f.write(script_content)

with open(os.path.join(staging_dir, "voiceover.mp3"), "wb") as f:
    f.write(b'\x00' * 1024)

print(f"Set up validation inputs in {staging_dir}")

# Mock Duration to 60.0s
# Default BEAT_MAX_DURATION is 12.0s
try:
    with patch('src.audio_engine.AudioAligner.get_audio_duration', return_value=60.0):
        import main
        
        # 1. Planning
        print("\n>>> VALIDATION STAGE: PLANNING <<<")
        sys.argv = ["main.py", "--run_id", run_id, "--version", str(version), "--stage", "planning"]
        main.main()
        
        # 2. Images (Sim) - Should PASS with Mock because we allowed it in Orchestrator for SIMULATION
        print("\n>>> VALIDATION STAGE: IMAGES (SIM) <<<")
        sys.argv = ["main.py", "--run_id", run_id, "--version", str(version), "--stage", "images", "--mode", "simulation"]
        main.main()

        print("\n>>> VALIDATION SUCCESS <<<")
        
        # Evidence Collection
        export_dir = os.path.join(base_dir, "exports", "VID_001")
        # Find the timestamped folder
        # We don't know the exact timestamp hash, so we find the one that contains 'run_VAL_001'
        for root, dirs, files in os.walk(export_dir):
            if "v1" in dirs and "run_VAL_001" in root:
                target_dir = os.path.join(root, "v1")
                print(f"\n>>> INSPECTING ARTIFACTS IN: {target_dir} <<<")
                
                for fname in ["qc_report.json", "manifest.json", "_READY.json"]:
                    fpath = os.path.join(target_dir, fname)
                    if os.path.exists(fpath):
                        print(f"\n--- {fname} ---")
                        with open(fpath, 'r') as f:
                            print(f.read())
                    else:
                         print(f"\n!!! MISSING {fname} !!!")

                spec_path = os.path.join(target_dir, "shot_spec.jsonl")
                if os.path.exists(spec_path):
                     print(f"\n--- shot_spec.jsonl (First 2 Lines) ---")
                     with open(spec_path, 'r') as f:
                         lines = f.readlines()
                         for line in lines[:2]:
                             print(line.strip())
                break

except Exception as e:
    print(f"\n>>> VALIDATION FAILED: {e}")
    import traceback
    traceback.print_exc()
