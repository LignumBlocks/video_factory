from pydantic import BaseModel, Field, model_validator, validator
from typing import List, Optional, Dict
from enum import Enum

# --- ENUMS ---
class AlignmentSource(str, Enum):
    MOCK_PROPORTIONAL = "mock_proportional"
    FORCED_ALIGNMENT = "forced_alignment"
    WHISPER_API = "whisper_api"

class ImageRole(str, Enum):
    START_REF = "start_ref"
    END_REF = "end_ref"
    EXTRA_KEYFRAME = "extra_keyframe"

class PairRole(str, Enum):
    START_REF = "start_ref"
    END_REF = "end_ref"

class AccentColor(str, Enum):
    NEGATIVE = "#B23A48"  # Red/negative sentiment
    POSITIVE = "#2F7D66"  # Green/positive sentiment

class CameraMovement(str, Enum):
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    TRACKING = "tracking"

class ShotSize(str, Enum):
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"

class CameraAngle(str, Enum):
    EYE_LEVEL = "eye_level"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    OVERHEAD = "overhead"

class QCStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"

class GenerationMode(str, Enum):
    SIMULATION = "simulation"
    REAL = "real"
    NONE = "none"

# --- CORE ATOM ---
class CameraSpec(BaseModel):
    movement: CameraMovement
    shot_size: ShotSize
    angle: CameraAngle
    strength: float = 0.5 

class ContinuitySpec(BaseModel):
    character_id: Optional[str] = None
    palette_id: Optional[str] = None

class ShotSpec(BaseModel):
    id: str = Field(..., description="Unique shot ID per run")
    beat_id: str
    run_id: str
    video_id: str
    
    # Timing
    beat_start_s: float
    beat_end_s: float
    duration_s: float
    
    # Intent & Content (Strict Validation)
    script_text: str
    metaphor: str
    intent: str
    phase_start_intent: Optional[str] = None 
    phase_end_intent: Optional[str] = None

    # [GATE 1] Explicit Narrative Structure
    # [GATE 1] Explicit Narrative Structure (Mandatory)
    block_id: str = Field(..., description="Block ID e.g. B01")
    dramatic_role: str = Field(..., description="Dramatic role e.g. problem")
    
    @model_validator(mode='after')
    def validate_intents(self):
        # Logic to BLOCK if critical phase intents are missing in context
        return self
    
    # Visuals
    camera: CameraSpec
    continuity: ContinuitySpec
    seed: int
    alignment_source: AlignmentSource
    alignment_confidence: float

# --- PARTNER REQUESTS ---
class NanobananaRequest(BaseModel):
    request_id: str
    shot_id: str
    beat_id: str
    
    pair_role: PairRole
    end_static: bool = False
    props_count: int = 0
    accent_color: Optional[AccentColor] = None
    
    prompt: str
    negative_prompt: str
    model_id: str = "nano-banana-pro"
    
    # Validation & Routing
    style_bible_hash: str
    ab_plan: Optional[str] = None
    ab_changes_count: int = 0
    
    # Img2Img Support (Clean Score Jump)
    image_input_path: Optional[str] = None
    image_strength: float = 0.75 # Default for img2img sequence
    
    # Output control
    seed: int
    aspect_ratio: str = "16:9"
    resolution: str = "1K" # Default 1K (User controlled quality)


class VeoRequest(BaseModel):
    request_id: str
    shot_id: str
    beat_id: str
    
    prompt: str
    duration_s: float
    fps: int = 30 # STRICT
    
    seeds: Optional[int] = None  # Rango: 10000-99999 según Kie.ai docs
    aspect_ratio: str = "16:9"
    
    style_profile_id: str
    negative_profile_id: str
    
    image_ref_start: Optional[str] = None
    image_ref_end: Optional[str] = None

# --- RUN METADATA ---
class FileMetadata(BaseModel):
    filename: str
    path: str
    size_bytes: int
    md5_checksum: Optional[str] = None

class AlignmentStats(BaseModel):
    source: AlignmentSource
    max_drift_s: float
    gap_count: int
    coverage_pct: float
    confidence_avg: float
    fallback_used: bool

class GlobalConfig(BaseModel):
    project_id: str
    video_id: str
    run_id: str
    version: int
    script_hash: str
    
    style_bible_hash: str
    style_bible_path: Optional[str] = None
    resolution: str = "1920x1080"
    fps: int = 30
    global_seed: int
    audio_source_file: str
    
    min_beat_duration_s: float = 2.0
    max_beat_duration_s: float = 12.0

class QCReport(BaseModel):
    status: QCStatus
    stage: str
    critical_flags: List[str]
    stop_pipeline: bool
    
    @model_validator(mode='after')
    def check_mock_stop(self):
        # Access attributes directly in V2 'after' validator
        if "MOCK_ALIGNMENT_USED" in self.critical_flags:
            self.stop_pipeline = True
            if self.status == QCStatus.PASS:
                self.status = QCStatus.WARN
        return self

class Manifest(BaseModel):
    video_id: str
    run_id: str
    version: int
    script_hash: str
    
    total_duration_s: float
    vo_duration_s: float
    
    alignment: AlignmentStats
    file_index: Dict[str, FileMetadata]
    export_dir: Optional[str] = None
    
    time_stretch_allowance: float = 0.05
    generation_mode: GenerationMode = GenerationMode.NONE

class ReadyFile(BaseModel):
    status: str = "READY"
    video_id: str
    run_id: str
    version: int
    script_hash: str
    alignment_source: AlignmentSource
    vo_duration_s: float
    manifest_checksum: str
    byte_size_map: Dict[str, int]
    generated_at: str
