
import pytest
import os
import json
from unittest.mock import MagicMock
from src.agents.beat_segmenter import BeatSegmenterAgent
from src.agents.beat_models import BeatLLMResponse
from src.llm import LLMClient, LLMResponse

class MockLLM(LLMClient):
    def generate_json(self, request):
        # Return a generic beat for whatever chunk
        # Just 1 beat covering the whole chunk to keep it simple
        lines = request.messages[1].content.split("\n")[1:] # skip "Script to segment:"
        # Actually message format is complex, let's just assume valid response
        
        return LLMResponse(text="Mock", json={
            "beats": [
                {
                    "order": 1,
                    "line_start": 1,
                    "line_end": 1, # Just 1 line beat
                    "intent": "Mock Beat",
                    "estimated_seconds": 3.0,
                    "priority": 2
                }
            ]
        })
    def generate_text(self, request):
        return LLMResponse(text="Mock")

@pytest.fixture
def segmenter():
    llm = MockLLM()
    # permissive config
    return BeatSegmenterAgent(llm, config={"min_beats": 1, "max_beats": 100})

def test_create_chunks_logic(segmenter):
    """Test splitting logic based on word count and markers."""
    # Create a dummy script with ~10 words per line
    # Target is 450 words. So ~45 lines.
    # We will make lines have 10 words exactly, no index prefix
    
    line_text = "word " * 10 
    narrable_lines = [line_text.strip() for _ in range(100)] # 1000 words total, 10 words/line
    
    # partial markers simulation
    markers = []
    
    # Case 1: No markers, strict limit 450 words -> 45 lines.
    chunks = segmenter._create_chunks(narrable_lines, markers)
    
    # 100 lines total. 45 lines = 450 words.
    # Chunk 1 should have exactly 45 lines?
    # Loop:
    # line 0..44 (45 lines) -> 450 words.
    # condition: >= 450. True. Split.
    # So chunk is 45 lines.
    
    # Debug info
    print(f"Chunk 1 len: {len(chunks[0]['lines'])}")
    
    assert len(chunks) >= 2
    assert len(chunks[0]['lines']) == 45
    
    # Case 2: With markers
    # Marker at line 30 (index 29). applies_after_narrable_index = 29.
    # Trigger splitting at 30 lines (300 words) which is > 0.6 * 450 (270).
    markers = [{'marker_type': 'SECTION', 'applies_after_narrable_index': 29}]
    
    chunks_marked = segmenter._create_chunks(narrable_lines, markers)
    # Expected: Split at 30 lines due to marker preference
    assert len(chunks_marked[0]['lines']) == 30
    assert chunks_marked[0]['offset'] == 0
    assert chunks_marked[1]['offset'] == 30
    
def test_segment_script_reassembly(segmenter, tmp_path):
    """Verify that beats from chunks are re-assembled with correct indices."""
    run_id = "test_chunk_run"
    
    # We need enough text to trigger chunking OR valid chunks
    # But segmenter._create_chunks is hardcoded to 450 words.
    # Let's mock _create_chunks to return 2 small chunks for testing reassembly
    
    segmenter._create_chunks = MagicMock(return_value=[
        {"lines": ["Line A " * 10], "offset": 0, "global_start_index": 1}, # Long enough to not merge
        {"lines": ["Line B " * 10], "offset": 1, "global_start_index": 2}
    ])
    
    # Mock prepare script to return 2 lines
    segmenter._prepare_script = MagicMock(return_value=(["Line A " * 10, "Line B " * 10], []))
    
    # Mock LLM is returning 1 beat (line 1-1) for each call.
    # We assume MockLLM returns beat for line 1-1.
    
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        beats, meta = segmenter.segment_script(run_id, "dummy text")
        
        assert len(beats) == 2
        # Beat 1: Line 1
        assert beats[0].source.line_start == 1
        assert beats[0].source.line_end == 1
        
        # Beat 2: Line 2
        assert beats[1].source.line_start == 2
        assert beats[1].source.line_end == 2
        
        # Verify order
        assert beats[0].order == 1
        assert beats[1].order == 2
        
    finally:
        os.chdir(original_cwd)
