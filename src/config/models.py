from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator
import re

# --- Shot Menu Models ---

class ShotConstraints(BaseModel):
    allow_amber: bool = False
    allow_particles: bool = False
    allow_text_like_shapes: bool = False

class ShotAllowed(BaseModel):
    energy: List[str] = ["low", "med", "high"] # Default validation set
    camera: List[str] = []

class PromptHints(BaseModel):
    visuals: List[str] = []
    motion: List[str] = []
    composition: List[str] = []

class ShotType(BaseModel):
    id: str = Field(..., description="Unique Shot ID in UPPER_SNAKE_CASE")
    description: str
    allowed: ShotAllowed
    constraints: ShotConstraints
    prompt_hints: PromptHints = PromptHints()

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v):
        if not re.match(r"^[A-Z][A-Z0-9_]{2,32}$", v):
            raise ValueError(f"Shot ID '{v}' must match UPPER_SNAKE_CASE regex.")
        return v

class ShotMenuConfig(BaseModel):
    schema_version: str = "1.0"
    menu_id: str
    shot_types: List[ShotType]

    @field_validator("shot_types")
    @classmethod
    def validate_unique_ids(cls, v):
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate Shot IDs found in menu.")
        return v


# --- System Rules Models ---

class RunModeDefaults(BaseModel):
    duration_s_default: int = 8
    duration_policy: str = "fixed"
    edit_window_s_default: int = 4

class DurationsConfig(BaseModel):
    clip_min_s: int = 8
    clip_max_s: int = 8
    enforce_exact: bool = True
    
    @field_validator("enforce_exact")
    @classmethod
    def validate_exact(cls, v, info):
        if v:
            values = info.data
            if values.get("clip_min_s") != values.get("clip_max_s"):
                # Note: In V2, previous values are accessed via info.data
                pass
        return v

class GuardrailsConfig(BaseModel):
    required_negative_terms: List[str]
    forbidden_prompt_terms: List[str]
    amber_rule: Dict[str, Any]
    closed_system_rule: Dict[str, Any]

class ModelConfig(BaseModel):
    target: str
    fps: Optional[int] = 30
    aspect_ratio: Optional[str] = "9:16"
    duration_s: Optional[int] = 8
    enabled: bool = True

class ModelsConfig(BaseModel):
    video: ModelConfig
    init_frame: ModelConfig

class AgentSettings(BaseModel):
    beat_segmenter: Dict[str, Any]
    visual_planner: Dict[str, Any]
    prompt_builder: Dict[str, Any]
    prompt_sanitizer: Dict[str, Any]

class SystemRulesConfig(BaseModel):
    schema_version: str = "1.0"
    run_mode_defaults: RunModeDefaults
    durations: DurationsConfig
    guardrails: GuardrailsConfig
    models: ModelsConfig
    agent_settings: AgentSettings
