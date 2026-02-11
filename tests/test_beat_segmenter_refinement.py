
import pytest
from unittest.mock import MagicMock, ANY
from src.agents.beat_segmenter import BeatSegmenterAgent, Beat, BeatSource
from src.llm import LLMClient, LLMJsonRequest, LLMResponse, LLMUsage, LLMJsonSchemaViolationError

class MockLLMClient(LLMClient):
    def __init__(self, beats_to_return=None):
        self.beats_to_return = beats_to_return or []
        
    def generate_json(self, request: LLMJsonRequest) -> LLMResponse:
        return LLMResponse(
            text="",
            json={"beats": self.beats_to_return},
            usage=LLMUsage(),
            model="mock"
        )
        
    def generate_text(self, request):
        pass

@pytest.fixture
def agent():
    return BeatSegmenterAgent(MockLLMClient())

# 1. Atomic Normalization Test
def test_atomic_normalization(agent):
    script = """# Header
    
    First sentence. Second sentence!
    - Bullet 1
    - Bullet 2
    
    Third sentence?
    """
    lines = agent._prepare_script(script)
    
    # Expected atomic units
    expected = [
        "# Header",
        "First sentence.",
        "Second sentence!",
        "- Bullet 1",
        "- Bullet 2",
        "Third sentence?"
    ]
    assert lines == expected


# 2. Text == Slice Contract Test
def test_text_matches_source_slice(agent):
    script_lines = ["Line 1", "Line 2", "Line 3", "Line 4"]
    
    # Simulate LLM outputting ranges
    llm_beats = [
        {"order": 1, "line_start": 1, "line_end": 2, "intent": "A", "estimated_seconds": 2.0, "priority": 1},
        {"order": 2, "line_start": 3, "line_end": 3, "intent": "B", "estimated_seconds": 1.0, "priority": 1},
        {"order": 3, "line_start": 4, "line_end": 4, "intent": "C", "estimated_seconds": 1.0, "priority": 1}
    ]
    
    from src.agents.beat_models import BeatLLMResponse
    llm_resp_objs = [BeatLLMResponse(**d) for d in llm_beats]
    
    beats, meta = agent._post_process("run_test", script_lines, llm_resp_objs, min_expected=1, max_expected=10)
    
    # Check Contract
    for b in beats:
        expected_text = "\n".join(script_lines[b.source.line_start-1 : b.source.line_end])
        assert b.text == expected_text, f"Beat {b.beat_id} text mismatch"

# 3. Duplicate Source Warning (implied by design logic, but let's check overlap handling)
def test_split_long_beats_updates_source(agent):
    # Setup a long beat (Needs > 7.0s duration -> > ~20 words)
    long_line = "This is a very long sentence that has enough words to be considered long by the duration calculator which uses roughly 2.8 words per second so we need about 20 words."
    script_lines = [long_line] * 6 # 6 lines of long text
    
    # Beat text is "Line1\nLine2...Line6". 
    full_text = "\n".join(script_lines)
    
    long_beat = Beat(
        run_id="test", beat_id="b1", order=1,
        text=full_text,
        intent="Long", estimated_seconds=20.0, priority=1,
        source=BeatSource(line_start=1, line_end=6)
    )
    
    splits = agent._split_long_beats([long_beat], script_lines)
    
    assert len(splits) > 1
    
    # Check completeness
    covered_lines = []
    for b in splits:
        # Check atomic contract
        expected = "\n".join(script_lines[b.source.line_start-1 : b.source.line_end])
        assert b.text == expected
        covered_lines.extend(range(b.source.line_start, b.source.line_end + 1))
        
    # Ensure sequential coverage without gaps/overlaps in the split
    covered_lines.sort()
    assert covered_lines == [1, 2, 3, 4, 5, 6]


# 4. Strict Schema Limits
def test_schema_enforces_limits(agent):
    # This tests the _get_segmentation_from_llm call logic
    # We mock the LLM to inspect the request sent 
    
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = LLMResponse(text="", json={"beats":[]}, usage=LLMUsage())
    
    agent.llm = mock_llm
    
    agent._get_segmentation_from_llm("run", "script", min_beats=10, max_beats=20)
    
    # Inspect call args
    call_args = mock_llm.generate_json.call_args
    req = call_args[0][0] # First arg is request
    
    schema = req.json_schema
    assert schema["properties"]["beats"]["minItems"] == 10
    assert schema["properties"]["beats"]["maxItems"] == 20
