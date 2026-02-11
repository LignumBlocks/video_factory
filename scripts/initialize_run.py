
import argparse
import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.orchestrator import RunOrchestrator

def main():
    parser = argparse.ArgumentParser(description="Initialize a RUN without execution.")
    parser.add_argument("--script", required=True, help="Path to script")
    parser.add_argument("--audio", required=True, help="Path to audio")
    parser.add_argument("--bible", required=True, help="Path to bible")
    
    args = parser.parse_args()
    
    # Initialize Orchestrator
    orchestrator = RunOrchestrator()
    
    print(f"Initializing RUN: {orchestrator.run_id}")
    
    # Initialize Run (Create Manifest + Freeze Inputs)
    orchestrator.initialize_run(args.script, args.audio, args.bible)
    
    print(f"RUN CREATED: {orchestrator.run_id}")
    
    # Verify Manifest content
    manifest_path = os.path.join(orchestrator.run_dir, "run_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            data = json.load(f)
            print("Verifying Manifest Fields...")
            print(f"Run ID: {data.get('run_id')}")
            print(f"App Version: {data.get('app_version')}")
            print(f"Git Commit: {data.get('git_commit')}")
            
            if "git_commit" not in data or "app_version" not in data:
                print("FAILED: Missing required fields in manifest")
                sys.exit(1)
            else:
                print("SUCCESS: Manifest contains required fields.")
    else:
        print(f"FAILED: Manifest not found at {manifest_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
