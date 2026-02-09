import re
import math
from typing import List, Tuple
from .models import BeatSheetRow, ClipPlanRow, VoSpanRef, ClipConstraints
from .enums import BeatVerb, BeatState, BeatLayer, BeatIntensity, ClipActionCategory
from .action_library import ACTION_LIBRARY # LOCKED catalog

class BeatPlanner:
    def __init__(self):
        pass

    def plan_beats(self, script_text: str) -> List[BeatSheetRow]:
        """
        Splits script into beats and assigns structural metadata based on section heuristics.
        """
        sentences = self._split_text(script_text)
        total = len(sentences)
        if total == 0:
            return []

        beats = []
        
        # Calculate thresholds
        idx_intro_end = math.floor(total * 0.2)
        idx_middle_end = math.floor(total * 0.9)
        if total > 1 and idx_middle_end == total:
             idx_middle_end = total - 1
        
        current_ms = 0
        
        for i, (sentence, length) in enumerate(sentences):
            beat_id = f"B{i+1:04d}" # B0001 format
            sequence_index = i + 1
            
            # Estimate duration in ms (approx 60ms per char)
            duration_ms = length * 60
            span_ref = VoSpanRef(start_ms=current_ms, end_ms=current_ms + duration_ms)
            current_ms += duration_ms
            
            # Determine Section & Attributes
            if i < idx_intro_end:
                # INTRO
                verb = BeatVerb.EXPECTATION
                state = BeatState.LOCKED
                layer = BeatLayer.BLUEPRINT
                intensity = BeatIntensity.L1
                amber = False
                shot_archetype = 1
                node_type_base = "GATE"
                node_role = "THRESHOLD"
            elif i < idx_middle_end:
                # MIDDLE
                verb = BeatVerb.TRACE
                state = BeatState.NOISY
                layer = BeatLayer.EVIDENCE
                intensity = BeatIntensity.L2
                amber = False
                shot_archetype = 7 # Mid-range
                node_type_base = "LEDGER"
                node_role = "RECORD"
            else:
                # END
                verb = BeatVerb.UNLOCK
                state = BeatState.UNLOCKED
                layer = BeatLayer.MICRO
                intensity = BeatIntensity.L3
                amber = True
                shot_archetype = 12 # Macro/Close
                node_type_base = "FILTER"
                node_role = "PURIFICATION"
            
            # Create Row
            row = BeatSheetRow(
                beat_id=beat_id,
                sequence_index=sequence_index,
                verb=verb,
                state=state,
                layer=layer,
                intensity=intensity,
                shot_archetype=shot_archetype,
                node_type_base=node_type_base,
                node_role=node_role,
                amber_allowed=amber,
                vo_summary=sentence[:150],
                vo_span_ref=span_ref
            )
            beats.append(row)

        return beats

    def assign_clip_plans(self, beats: List[BeatSheetRow]) -> List[ClipPlanRow]:
        """
        Maps BeatSheetRows to ClipPlanRows with strict archetype mapping.
        """
        plans = []
        for beat in beats:
            # Default values
            category = ClipActionCategory.GENERIC
            motion = "Static" # Default
            camera = "Locked" # Default
            
            # Logic based on Verb (LOCKED contract)
            if beat.verb == BeatVerb.EXPECTATION:
                category = ClipActionCategory.SNAPSHOT
                motion = "Minimal movement"
                camera = "Locked, wide angle"
            elif beat.verb == BeatVerb.TRACE:
                category = ClipActionCategory.LEDGER_IMPRINT
                motion = "Flowing lines, steady pace" 
                camera = "Tracking slow pan"
            elif beat.verb == BeatVerb.UNLOCK:
                category = ClipActionCategory.GATE_CLICK
                motion = "Mechanical, precise click"
                camera = "Macro focus, shallow depth"
            
            # RESOLVE ACTION INTENT FROM LIBRARY
            lib_entry = ACTION_LIBRARY.get(category, ACTION_LIBRARY[ClipActionCategory.GENERIC])
            
            if isinstance(lib_entry, dict):
                # Deterministic Selection Logic for Variants
                txt = beat.vo_summary.lower()
                
                # 1. First beat of sequence (Intro) -> REST
                if beat.sequence_index == 1 and category == ClipActionCategory.SNAPSHOT:
                    intent = lib_entry.get("REST", list(lib_entry.values())[0])
                    
                # 2. Keyword triggers (Only for SNAPSHOT)
                elif category == ClipActionCategory.SNAPSHOT and ("650" in txt or "lower" in txt):
                     intent = lib_entry.get("PRESS_DEEP", list(lib_entry.values())[0])
                elif category == ClipActionCategory.SNAPSHOT and ("710" in txt or "higher" in txt):
                     intent = lib_entry.get("PRESS_LIGHT", list(lib_entry.values())[0])
                     
                # 3. Fallback: Round Robin based on sequence index
                else:
                    # e.g. B0003 (idx=3) -> index 3
                    # Variants keys: REST, PRESS_DEEP, PRESS_LIGHT (ordered insertion in Py3.7+)
                    keys = list(lib_entry.keys())
                    k_idx = beat.sequence_index % len(keys)
                    intent = lib_entry[keys[k_idx]]
            else:
                # Standard single string
                intent = lib_entry

            # Constraints
            constraints = ClipConstraints(
                no_humans=True,
                no_text=True,
                no_markings=True,
                closed_system_only=True,
                amber_allowed=beat.amber_allowed
            )
            
            plan = ClipPlanRow(
                beat_id=beat.beat_id,
                action_intent=intent,
                action_intent_category=category,
                motion_profile=motion,
                camera_behavior=camera,
                constraints=constraints
            )
            plans.append(plan)
            
        return plans

    def _split_text(self, text: str) -> List[Tuple[str, int]]:
        """
        Splits by sentence punctuation but keeps it simple.
        Returns list of (text_chunk, length_in_chars).
        """
        pattern = r'(?<=[.!?])\s+'
        chunks = re.split(pattern, text.strip())
        
        result = []
        for c in chunks:
            if c.strip():
                result.append((c.strip(), len(c) + 1))
        
        return result
