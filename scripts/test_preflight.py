
import os
import sys
import shutil
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.orchestrator import RunOrchestrator

ARTIFACTS_ROOT = "artifacts_test"
INPUTS_ROOT = "inputs_test"

def setup_inputs():
    if os.path.exists(INPUTS_ROOT): shutil.rmtree(INPUTS_ROOT)
    os.makedirs(INPUTS_ROOT)
    
    # Valid files
    with open(f"{INPUTS_ROOT}/valid_script.txt", "w") as f: f.write("Hello World")
    
    # Create valid dummy MP3 (requires minimal header or mutagen mock)
    # We'll just copy the dummy_vo.mp3 if exists, or assume we have one.
    # If not, create a text file mimicking format if validator allows? 
    # But validator uses MP3() from mutagen.
    # So we strictly need a valid mp3. 
    # Let's use the one in current dir 'dummy_vo.mp3'
    if not os.path.exists("dummy_vo.mp3"):
        print("WARNING: dummy_vo.mp3 not found. Skipping audio validity specific tests or failing.")
        
    shutil.copy("dummy_vo.mp3", f"{INPUTS_ROOT}/valid_audio.mp3")
    
    # Valid Bible
    with open(f"{INPUTS_ROOT}/valid_bible.md", "w") as f: f.write("# Title\nLOCKED: Clean Score Jump\nContent...")

    # Invalid files
    with open(f"{INPUTS_ROOT}/empty_script.txt", "w") as f: pass
    with open(f"{INPUTS_ROOT}/invalid_bible.md", "w") as f: f.write("DRAFT MODE")
    with open(f"{INPUTS_ROOT}/zero_audio.mp3", "w") as f: pass

def test_happy_path():
    print("\n--- TEST: Happy Path ---")
    if os.path.exists(ARTIFACTS_ROOT): shutil.rmtree(ARTIFACTS_ROOT)
    
    # Patch config path for orchestrator to use test artifacts? 
    # Actually RunOrchestrator loads AppConfig. We can override via env.
    os.environ["APP__PATHS__ARTIFACTS_ROOT"] = ARTIFACTS_ROOT
    
    orch = RunOrchestrator()
    orch.initialize_run(
        f"{INPUTS_ROOT}/valid_script.txt",
        f"{INPUTS_ROOT}/valid_audio.mp3",
        f"{INPUTS_ROOT}/valid_bible.md"
    )
    
    # Verify Manifest
    m_path = os.path.join(orch.run_dir, "run_manifest.json")
    with open(m_path) as f: m = json.load(f)
    print(f"Status: {m['status']['state']}")
    assert m['status']['state'] == "NOT_STARTED" # Ingest complete -> NOT_STARTED of Planning
    assert m['status']['phase'] == "PLANNING"
    print("PASS")

def test_fail_empty_script():
    print("\n--- TEST: Fail Empty Script ---")
    orch = RunOrchestrator()
    orch.initialize_run(
        f"{INPUTS_ROOT}/empty_script.txt",
        f"{INPUTS_ROOT}/valid_audio.mp3",
        f"{INPUTS_ROOT}/valid_bible.md"
    )
    
    m_path = os.path.join(orch.run_dir, "run_manifest.json")
    with open(m_path) as f: m = json.load(f)
    print(f"Status: {m['status']['state']}")
    assert m['status']['state'] == "FAILED_PREFLIGHT"
    
    r_path = os.path.join(orch.run_dir, "preflight_report.json")
    with open(r_path) as f: r = json.load(f)
    print(f"Report Script: {r['script']}")
    assert r['script']['status'] == "FAIL"
    print("PASS")

def test_fail_invalid_bible():
    print("\n--- TEST: Fail Invalid Bible (No LOCKED) ---")
    orch = RunOrchestrator()
    orch.initialize_run(
        f"{INPUTS_ROOT}/valid_script.txt",
        f"{INPUTS_ROOT}/valid_audio.mp3",
        f"{INPUTS_ROOT}/invalid_bible.md"
    )
    
    m_path = os.path.join(orch.run_dir, "run_manifest.json")
    with open(m_path) as f: m = json.load(f)
    assert m['status']['state'] == "FAILED_PREFLIGHT"
    
    r_path = os.path.join(orch.run_dir, "preflight_report.json")
    with open(r_path) as f: r = json.load(f)
    print(f"Report Bible: {r['bible']}")
    assert r['bible']['status'] == "FAIL"
    print("PASS")

if __name__ == "__main__":
    setup_inputs()
    test_happy_path()
    test_fail_empty_script()
    test_fail_invalid_bible()
