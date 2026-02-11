"""
T-103: Beat data models
"""
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
import json

@dataclass
class BeatSource:
    """Source line information for traceability"""
    line_start: int
    line_end: int

@dataclass
class Beat:
    """
    Single narrative beat (T-103.1).
    
    This is the OUTPUT format written to beat_sheet.jsonl.
    """
    run_id: str
    beat_id: str
    order: int
    text: str
    intent: str
    estimated_seconds: float
    priority: int
    source: BeatSource
    agent_version: str = "BeatSegmenter/1.0"
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().astimezone().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization"""
        d = asdict(self)
        # Convert BeatSource to dict
        d["source"] = {"line_start": self.source.line_start, "line_end": self.source.line_end}
        return d
    
    def to_jsonl_line(self) -> str:
        """Convert to JSONL line (single line JSON)"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

@dataclass
class BeatLLMResponse:
    """
    LLM output format (T-103.3 Step B).
    
    This is what the LLM returns - NO text field, only line ranges.
    Text is computed deterministically from script lines.
    """
    order: int
    line_start: int
    line_end: int
    intent: str
    estimated_seconds: float
    priority: int = 1

@dataclass
class BeatSheetMeta:
    """Metadata for beat_sheet.meta.json"""
    total_beats: int
    avg_estimated_seconds: float
    min_beats: int
    max_beats: int
    warnings: list
    visual_contamination_count: int = 0
    # T-103 Refinements
    normalized_line_count: int = 0
    word_count: int = 0
    estimated_duration_s: float = 0.0
    target_beats: int = 0
    structural_markers_count: int = 0
    structural_markers_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
