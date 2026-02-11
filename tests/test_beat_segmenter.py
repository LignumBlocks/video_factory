"""
T-103 Tests: BeatSegmenterAgent
Reflects fixes for Gap Filling, Strict Normalization, Duration Clamping.
"""
import pytest
import json
from src.agents.beat_segmenter import BeatSegmenterAgent
from src.agents.beat_models import BeatLLMResponse
from src.llm import MockLLMClient, LLMMessage, LLMJsonRequest

@pytest.fixture
def script_lines():
    return [
        "Line 1: Markets are weird.",
        "Line 2: Data is flowing.",
        "Line 3: Clarity is key.",
        "Line 4: Deep insights.",
        "Line 5: Global ledger.",
        "Line 6: Precision and speed.",
        "Line 7: Future of finance."
    ]

@pytest.fixture
def agent():
    mock_llm = MockLLMClient({})
    return BeatSegmenterAgent(llm=mock_llm)

def test_ranges_build_text_from_lines(agent, script_lines):
    """AC: Text is accurately built from script ranges (and gaps filled)"""
    llm_beats = [
        BeatLLMResponse(order=1, line_start=1, line_end=2, intent="Intro", estimated_seconds=4.0, priority=1),
        BeatLLMResponse(order=2, line_start=3, line_end=4, intent="Insights", estimated_seconds=3.0, priority=1)
    ]
    
    beats, meta = agent._post_process("run123", script_lines, llm_beats)
    
    assert len(beats) == 2
    assert beats[0].text == "Line 1: Markets are weird.\nLine 2: Data is flowing."
    
    # The remaining lines (5-7) should be appended to the last beat due to gap filling
    expected_last_beat = "Line 3: Clarity is key.\nLine 4: Deep insights.\nLine 5: Global ledger.\nLine 6: Precision and speed.\nLine 7: Future of finance."
    assert beats[1].text == expected_last_beat
    assert "Merged end gap lines 5-7 into last beat" in meta.warnings

def test_gap_filling_middle(agent):
    """Test that gaps in the middle are filled"""
    # Use longer text to avoid merging
    long_line = "This is a sufficiently long line of text to ensure the beat is not merged unnecessarily."
    lines = [long_line, long_line, "Gap Content needs to be long enough too.", long_line, long_line]
    
    llm_beats = [
        BeatLLMResponse(order=1, line_start=1, line_end=2, intent="A", estimated_seconds=5.0, priority=1),
        BeatLLMResponse(order=2, line_start=4, line_end=5, intent="B", estimated_seconds=5.0, priority=1)
    ]
    
    beats, meta = agent._post_process("run", lines, llm_beats)
    
    # Should still be 2 beats, but first beat extended to include L3
    assert len(beats) == 2
    # Verify content of merged gap
    assert "Gap Content" in beats[0].text
    assert beats[0].source.line_end == 3 # Updated
    assert beats[1].text == f"{long_line}\n{long_line}"
    assert "Merged gap lines 3-3 into beat 1" in meta.warnings

def test_assigns_stable_beat_ids_after_sorting(agent, script_lines):
    """AC: IDs are b001, b002 even if LLM returns mixed order"""
    llm_beats = [
        BeatLLMResponse(order=2, line_start=3, line_end=4, intent="B", estimated_seconds=3.0, priority=1),
        BeatLLMResponse(order=1, line_start=1, line_end=2, intent="A", estimated_seconds=4.0, priority=1)
    ]
    
    beats, meta = agent._post_process("run123", script_lines, llm_beats)
    
    assert beats[0].beat_id == "b001"
    assert beats[0].intent == "A"
    assert beats[1].beat_id == "b002"
    assert beats[1].intent == "B"

def test_merge_short_beats_once(agent, script_lines):
    """AC: Short beats are merged into the next one"""
    from src.agents.beat_models import Beat, BeatSource
    
    # Text must be short or estimated seconds small
    b1 = Beat("r", "b001", 1, "Short", "I1", 1.0, 1, BeatSource(1, 1)) 
    b2 = Beat("r", "b002", 2, "Normal length text that is sufficiently long.", "I2", 4.0, 1, BeatSource(2, 2))
    b3 = Beat("r", "b003", 3, "Another beat", "I3", 3.0, 1, BeatSource(3, 3))
    
    merged = agent._merge_short_beats([b1, b2, b3])
    
    assert len(merged) == 2
    assert merged[0].text == "Short\nNormal length text that is sufficiently long."
    # Duration is 0.0 because it needs recalc (handled in post_process usually)
    assert merged[0].estimated_seconds == 0.0 
    assert "I1 | I2" in merged[0].intent

def test_visual_contamination_detection(agent):
    """AC: Visual keywords are detected strictly in intent"""
    # Intent contamination
    assert agent._detect_contamination("We see a camera") >= 2 # 'we see', 'camera'
    assert agent._detect_contamination("Pure narrative") == 0
    
    # Text contamination (specific phrases)
    assert agent._detect_text_contamination("Then we see the graph") >= 1 # 'we see'
    assert agent._detect_text_contamination("A camera shy person") == 0 # 'camera' alone not in TEXT_KEYWORDS
    assert agent._detect_text_contamination("Camera pans to left") >= 1 # 'camera pans' or 'pan to'

def test_duration_clamping_and_warnings(agent):
    """Test duration calculation and clamping"""
    # Create a text that produces > 12s
    # 2.8 words/sec -> > 33.6 words
    long_text = "word " * 40
    lines = [long_text, "Visual: We see a camera pan."]
    
    llm_beats = [
        BeatLLMResponse(order=1, line_start=1, line_end=1, intent="Visual: We see a camera pan.", estimated_seconds=5.0, priority=1),
        BeatLLMResponse(order=2, line_start=2, line_end=2, intent="Clean intent", estimated_seconds=2.0, priority=1)
    ]
    
    beats, meta = agent._post_process("run", lines, llm_beats)
    
    # Beat 1: Long text clamped
    assert beats[0].estimated_seconds == 12.0
    assert any("BEAT_TOO_LONG" in w for w in meta.warnings)
    
    # Beat 1: Intent contamination ("We see", "camera")
    assert any("[CONTAMINATION]" in w for w in meta.warnings)
    assert meta.visual_contamination_count > 0

def test_beat_segmenter_produces_jsonl_with_mock_llm(agent):
    """Integration style test with mock LLM client"""
    script = "Line 1\nLine 2\nLine 3"
    
    agent.llm._compute_request_hash = lambda req, include_schema=False: "FIXED_HASH"
    agent.llm.fixtures = {
        "FIXED_HASH": {
            "json": {
                "beats": [
                    {"order": 1, "line_start": 1, "line_end": 2, "intent": "A", "estimated_seconds": 5.0, "priority": 1},
                    {"order": 2, "line_start": 3, "line_end": 3, "intent": "B", "estimated_seconds": 3.0, "priority": 1}
                ]
            }
        }
    }
    
    beats, meta = agent.segment_script("run1", script)
    
    assert len(beats) >= 1
    assert beats[0].source.line_start == 1
    # Check text contains all lines
    all_text = "\n".join([b.text for b in beats])
    assert "Line 1" in all_text
    assert "Line 2" in all_text
    assert "Line 3" in all_text
