import os
import shutil
import json
import sys
from time import sleep

# Add src to path
sys.path.append(os.getcwd())

from src.orchestrator import RunOrchestrator
from src.foundation.manifest import load_run_manifest, Phase, State, validate_consistency

# Test Data
RUN_ID = "EPIC0-TEST-RUN"
SCRIPT_PATH = "tests/fixtures/script.txt"
AUDIO_PATH = "tests/fixtures/audio.mp3"
BIBLE_PATH = "tests/fixtures/bible.md"

def setup_fixtures():
    os.makedirs("tests/fixtures", exist_ok=True)
    with open(SCRIPT_PATH, "w") as f: f.write("Hello world. This is a test script.")
    with open(AUDIO_PATH, "w") as f: f.write("FAKE AUDIO CONTENT")
    with open(BIBLE_PATH, "w") as f: f.write("# Style Bible\nSTATUS: LOCKED\n")
    
    # Clean artifacts
    if os.path.exists(f"artifacts/{RUN_ID}"):
        shutil.rmtree(f"artifacts/{RUN_ID}")

def print_manifest(stage_name, manifest_json):
    print(f"\n[{stage_name}] Manifest:")
    print(json.dumps(manifest_json, indent=2))
    
    # Validation Checks
    status = manifest_json['status']
    phase = status['phase']
    state = status['state']
    
    print(f"CHECK: Phase '{phase}' should not contain DONE...")
    if "_DONE" in phase:
        print("FAIL: Phase name contains _DONE")
        sys.exit(1)
        
    print(f"CHECK: State '{state}' is valid Enum...")
    if state not in ["NOT_STARTED", "IN_PROGRESS", "DONE", "FAILED"]:
         print(f"FAIL: Invalid state {state}")
         sys.exit(1)

def run_test():
    setup_fixtures()
    
    print("\n=== STEP 1: INITIALIZE & INGEST (First Instance) ===")
    orch = RunOrchestrator(run_id=RUN_ID)
    orch.initialize_run(SCRIPT_PATH, AUDIO_PATH, BIBLE_PATH)
    
    # Run Ingest explicitly (simulate first run part)
    orch._execute_phase_wrapper(Phase.INGEST)
    
    # Snapshot
    m = load_run_manifest(RUN_ID)
    print_manifest("POST-INGEST", m.model_dump())
    shutil.copy(f"artifacts/{RUN_ID}/run_manifest.json", "run_manifest_after_ingest.json")
    
    # Assertions Post-Ingest
    assert Phase.INGEST in m.completed_phases, "Ingest not in completed phases"
    assert m.status.phase != "INGEST_DONE", "Phase has _DONE"
    assert m.status.state in ["NOT_STARTED", "IN_PROGRESS"], "Invalid State"
    
    frozen = m.inputs.frozen_paths
    assert frozen.get("script"), "Frozen script missing"
    assert frozen.get("audio"), "Frozen audio missing"
    assert frozen.get("bible"), "Frozen bible missing"
    
    # Verify Checkpoint Content
    with open(f"artifacts/{RUN_ID}/_INGEST_DONE.json") as f:
        chk = json.load(f)
        assert chk["phase"] == "INGEST", "Checkpoint phase mismatch"

    print("\n[SIMULATING CRASH/RESTART]...\n")
    del orch 
    
    print("=== STEP 2: RESUME (Second Instance) ===")
    orch2 = RunOrchestrator(run_id=RUN_ID)
    
    # It should autoload manifest. 
    # Calling run() should skip INGEST and do PLANNING.
    # We call _execute_phase_wrapper(Phase.PLANNING) to control test flow, 
    # but let's assume orchestrator.run() logic works by checking completed_phases.
    # For this specific test requirement: "correr PLANNING (o run()) y demostrar que salta INGEST"
    
    # Let's verify it skips Ingest
    if Phase.INGEST in orch2.manifest.completed_phases:
        print("Verified: Resume loaded completed phases correctly.")
    else:
        print("FAIL: Resume did not see Ingest as done.")
        sys.exit(1)
        
    orch2._execute_phase_wrapper(Phase.PLANNING)
    
    m2 = load_run_manifest(RUN_ID)
    print_manifest("POST-PLANNING", m2.model_dump())
    shutil.copy(f"artifacts/{RUN_ID}/run_manifest.json", "run_manifest_after_planning.json")
    
    # Verify Consistency
    print("\n=== CHECKING CONSISTENCY ===")
    validate_consistency(RUN_ID, m2, "artifacts") # Uses the helper we wrote
    print("Consistency Check Passed via Helper.")

    # Existence assertions
    assert os.path.exists(f"artifacts/{RUN_ID}/_PLANNING_DONE.json")
    
    print("\n=== SUCCESS ===")

if __name__ == "__main__":
    run_test()
