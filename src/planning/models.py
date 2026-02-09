

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict
from .enums import BeatVerb, BeatState, BeatLayer, BeatIntensity, ClipActionCategory

class VoSpanRef(BaseModel):
    start_ms: int
    end_ms: int

class BeatSheetRow(BaseModel):
    beat_id: str
    sequence_index: int
    verb: BeatVerb
    state: BeatState
    layer: BeatLayer
    intensity: BeatIntensity
    shot_archetype: int = Field(..., ge=1, le=12)
    node_type_base: str
    node_role: str
    amber_allowed: bool
    vo_summary: str
    vo_span_ref: VoSpanRef

    @model_validator(mode='after')
    def check_amber_constraint(self):
        if self.amber_allowed:
            # Hard constraint: Amber only if UNLOCK + L3
            if not (self.verb == BeatVerb.UNLOCK and self.intensity == BeatIntensity.L3):
                raise ValueError(f"Amber allowed forbidden for non-UNLOCK/L3 beats (Beat: {self.beat_id})")
        return self

class ClipConstraints(BaseModel):
    no_humans: bool = True
    no_text: bool = True
    no_markings: bool = True
    closed_system_only: bool = True
    amber_allowed: bool

class ClipPlanRow(BaseModel):
    beat_id: str
    action_intent: str
    action_intent_category: ClipActionCategory
    motion_profile: str
    camera_behavior: str
    constraints: ClipConstraints
