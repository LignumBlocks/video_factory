from typing import List
from .models import BeatSheetRow, ClipPlanRow, BeatVerb, BeatIntensity

def validate_scarcity(rows: List[BeatSheetRow], max_unlock_pct: float = 0.15):
    """
    Ensures UNLOCK beats are scarce (< max_unlock_pct of total).
    If total beats is small (< 5), implies max 1 unlock.
    """
    total = len(rows)
    if total == 0: return
    
    unlocks = sum(1 for r in rows if r.verb == BeatVerb.UNLOCK)
    pct = unlocks / total
    
    if pct > max_unlock_pct and unlocks > 1: # Allow 1 even if it's 100% of 1 beat
         raise ValueError(f"Scarcity Violation: UNLOCK beats constitute {pct:.1%} of total (> {max_unlock_pct:.1%}). Count: {unlocks}/{total}")

def validate_clip_plan_integrity(beat_rows: List[BeatSheetRow], clip_rows: List[ClipPlanRow]):
    """
    Cross-validates that every beat has a clip plan.
    """
    beat_ids = set(b.beat_id for b in beat_rows)
    plan_ids = set(c.beat_id for c in clip_rows)
    
    missing = beat_ids - plan_ids
    if missing:
        raise ValueError(f"Missing ClipPlans for beats: {missing}")
    
    # Archetype validation is now handled by BeatSheetRow Pydantic model
    return True
