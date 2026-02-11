
import os
import shutil
import pytest
from src.orchestrator import RunOrchestrator

INPUTS_ROOT = "inputs_test_structure"

@pytest.fixture
def setup_inputs():
    if os.path.exists(INPUTS_ROOT): shutil.rmtree(INPUTS_ROOT)
    os.makedirs(INPUTS_ROOT)
    
    with open(f"{INPUTS_ROOT}/script.txt", "w") as f: f.write("Structure Test Script")
    # Use valid dummy MP3 from project root
    if os.path.exists("dummy_vo.mp3"):
        shutil.copy("dummy_vo.mp3", f"{INPUTS_ROOT}/voiceover.mp3")
    else:
        # Should fail if not present as test depends on it
        pytest.fail("dummy_vo.mp3 not found in project root") 
    with open(f"{INPUTS_ROOT}/bible.md", "w") as f: f.write("LOCKED: Structure Test")
    
    yield
    
    # Cleanup runs created? 
    # Maybe keep for inspection if failed, but cleaner to rely on artifacts_test dir
    pass

def test_run_structure_generation(setup_inputs):
    # Use a specific test artifacts dir
    test_artifacts = "artifacts_structure_test"
    if os.path.exists(test_artifacts): shutil.rmtree(test_artifacts)
    
    os.environ["APP__PATHS__ARTIFACTS_ROOT"] = test_artifacts
    
    orch = RunOrchestrator()
    orch.initialize_run(
        f"{INPUTS_ROOT}/script.txt",
        f"{INPUTS_ROOT}/voiceover.mp3",
        f"{INPUTS_ROOT}/bible.md"
    )
    
    # Check ID format
    run_id = orch.run_id
    assert "_" in run_id
    parts = run_id.split("_")
    assert len(parts) >= 3 # YYYYMMDD_HHMMSS_HASH
    
    run_dir = os.path.join(test_artifacts, run_id)
    assert os.path.exists(run_dir)
    
    # Check Folder Structure
    expected_folders = [
        "inputs",
        "work/beats",
        "work/prompts",
        "work/frames",
        "work/clips",
        "work/qc",
        "work/assembly",
        "outputs",
        "logs"
    ]
    for folder in expected_folders:
        path = os.path.join(run_dir, folder)
        assert os.path.exists(path), f"Missing folder: {folder}"
        assert os.path.isdir(path)
        
    # Check Inputs Copied and Renamed
    assert os.path.exists(os.path.join(run_dir, "inputs/script.txt"))
    assert os.path.exists(os.path.join(run_dir, "inputs/voiceover.mp3"))
    assert os.path.exists(os.path.join(run_dir, "inputs/style_bible_LOCKED.md")) # Renamed
    
    # Check Manifest
    assert os.path.exists(os.path.join(run_dir, "run_manifest.json"))

def test_deterministic_id(setup_inputs):
    test_artifacts = "artifacts_structure_test_2"
    os.environ["APP__PATHS__ARTIFACTS_ROOT"] = test_artifacts
    
    # Run 1
    orch1 = RunOrchestrator()
    orch1.initialize_run(
        f"{INPUTS_ROOT}/script.txt",
        f"{INPUTS_ROOT}/voiceover.mp3",
        f"{INPUTS_ROOT}/bible.md"
    )
    id1 = orch1.run_id
    
    # Run 2 (Same inputs)
    orch2 = RunOrchestrator()
    orch2.initialize_run(
        f"{INPUTS_ROOT}/script.txt",
        f"{INPUTS_ROOT}/voiceover.mp3",
        f"{INPUTS_ROOT}/bible.md"
    )
    id2 = orch2.run_id
    
    # Timestamps will differ, but hash part should be identical
    hash1 = id1.split("_")[-1]
    hash2 = id2.split("_")[-1]
    
    assert hash1 == hash2
