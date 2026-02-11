
import pytest
import os
import json
from unittest.mock import MagicMock
from src.agents.beat_segmenter import BeatSegmenterAgent
from src.llm import LLMClient, LLMResponse

class MockLLM(LLMClient):
    def generate_json(self, request):
        # Mock response for segmentation
        return LLMResponse(text="Mock response", json={
            "beats": [
                {
                    "order": 1,
                    "line_start": 1,
                    "line_end": 1,
                    "intent": "Intro hook",
                    "estimated_seconds": 3.0,
                    "priority": 3
                },
                {
                    "order": 2,
                    "line_start": 2,
                    "line_end": 2,
                    "intent": "Second sentence",
                    "estimated_seconds": 3.0,
                    "priority": 2
                }
            ]
        })

    def generate_text(self, request):
        return LLMResponse(text="Mock text response")

@pytest.fixture
def segmenter():
    llm = MockLLM()
    config = {"min_beats": 1, "max_beats": 100}
    return BeatSegmenterAgent(llm, config)

def test_prepare_script_separation(segmenter):
    """Verify that structural lines are separated from narrable lines."""
    input_text = """## Header 1
Narrable line one.
---
Narrable line two.
## Header 2"""
    
    narrable, markers = segmenter._prepare_script(input_text)
    
    assert len(narrable) == 2
    assert narrable[0] == "Narrable line one."
    assert narrable[1] == "Narrable line two."
    
    assert len(markers) == 3
    assert markers[0]["text"] == "## Header 1"
    assert markers[0]["marker_type"] == "SECTION"
    assert markers[1]["text"] == "---"
    assert markers[1]["marker_type"] == "SEPARATOR"
    assert markers[2]["text"] == "## Header 2"

def test_fill_gaps_ignores_structural(segmenter):
    """Verify that gap filling logic works on narrable lines context."""
    # Context: Narrable lines = ["A", "B", "C"]
    # Beats cover 1-1 and 3-3. Gap at 2.
    narrable_lines = ["Line A.", "Line B (Gap).", "Line C."]
    
    beats_input = [
        MagicMock(source=MagicMock(line_start=1, line_end=1), order=1),
        MagicMock(source=MagicMock(line_start=3, line_end=3), order=2)
    ]
    # Behave like real Beat objects roughly
    beats_input[0].text = "Line A."
    beats_input[0].run_id = "test_run"
    beats_input[1].text = "Line C."
    beats_input[1].run_id = "test_run"
    
    filled, warnings = segmenter._fill_gaps(narrable_lines, beats_input)
    
    # Gap at line 2 should be merged into beat 1
    assert len(filled) == 2
    assert "Line B (Gap)." in filled[0].text
    assert filled[0].source.line_end == 2

def test_end_to_end_artifacts(segmenter, tmp_path):
    """Verify full process generates correct artifacts and metadata."""
    run_id = "test_run_structural"
    script = """## Header
This is a long enough line 1 to avoid being merged by the short beat logic automatically.
---
This is a long enough line 2 to also stand on its own as a separate beat."""
    
    # Mock file writing by changing CWD or mocking open? 
    # Easiest is to let it write to tmp_path/runs/... but code uses relative paths "runs/..."
    # We will simulate valid run env by chdir or patching os.path.join?
    # Let's just trust unit tests for logic and test return values here.
    
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        beats, meta = segmenter.segment_script(run_id, script)
        
        # Check return
        assert len(beats) == 2
        assert meta.structural_markers_count == 2
        assert meta.normalized_line_count == 2 # 2 narrable lines
        
        # Check artifacts
        work_dir = tmp_path / "runs" / run_id / "work"
        assert (work_dir / "normalized_script_narrable.txt").exists()
        assert (work_dir / "structural_markers.jsonl").exists()
        
        # Verify content
        with open(work_dir / "normalized_script_narrable.txt") as f:
            content = f.read()
            assert "## Header" not in content
            assert "---" not in content
            assert "This is a long enough line 1" in content
            
        with open(work_dir / "structural_markers.jsonl") as f:
            markers = [json.loads(line) for line in f]
            assert len(markers) == 2
            assert markers[0]["text"] == "## Header"
            
    finally:
        os.chdir(original_cwd)
