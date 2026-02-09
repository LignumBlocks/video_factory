from typing import List
from src.planning.models import BeatSheetRow, ClipPlanRow
from src.prompts.models import PromptRow, PromptPack
from src.prompts.sanitizer import PromptSanitizer
from src.prompts.vocabulary import NEGATIVE_PROMPT_DEFAULT, HARD_LOCK_INJECTION

class PromptGenerator:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.sanitizer = PromptSanitizer()


    def generate_prompts(self, beats: List[BeatSheetRow], clips: List[ClipPlanRow]) -> PromptPack:
        """
        Generates prompts strictly adhering to LOCKED contract.
        """
        clip_map = {c.beat_id: c for c in clips}
        prompts = []
        
        for beat in beats:
            clip = clip_map.get(beat.beat_id)
            if not clip:
                print(f"WARNING: Skipping Beat {beat.beat_id} - No Clip Plan")
                continue
            
            # 1. PASS A: Init Frame (Static, World Only)
            # Must NOT have action. Context only.
            
            # Safe Visual Mapping for Layers
            layer_map = {
                "blueprint": "Technical Schematic",
                "evidence": "Clean Technical Structure",
                "micro": "Macro Photography Detail",
                "data": "Abstract Data Flow"
            }
            # Normalize enum value for lookup
            raw_layer = str(beat.layer).split('.')[-1].lower() if '.' in str(beat.layer) else str(beat.layer).lower()
            layer_val = layer_map.get(raw_layer, "Abstract Technical Background")

            # Safe Visual Mapping for Aesthetics
            aesthetic_map = {
                "snapshot": "static still-life composition",
                "ledger_imprint": "clean ledger-like surface geometry",
                "gate_click": "precision mechanical detail",
                "filter_wash": "smooth fluid motion",
                "stair_step": "stepped geometric progression",
                "throttle": "controlled mechanical flow",
                "breath": "organic rhythmic expansion"
            }
            raw_aesthetic = str(clip.action_intent_category.value).lower()
            aesthetic_val = aesthetic_map.get(raw_aesthetic, "clean minimalist aesthetic")
            
            raw_init = f"Abstract background representing {layer_val}, {aesthetic_val}, static scene, {HARD_LOCK_INJECTION}"
            
            # Sanitization (Pass A)
            clean_init, report_init = self.sanitizer.clean(raw_init, beat.amber_allowed)
            
            # 2. PASS B: Clip Prompt (One Action)
            # Action = clip_plan.action_intent (Source of Truth)
            raw_clip = f"{clip.action_intent}, {HARD_LOCK_INJECTION}"
            
            # Sanitization (Pass B)
            clean_clip, report_clip = self.sanitizer.clean(raw_clip, beat.amber_allowed)
            
            # Merge Reports (If any block found, list it)
            # Explicitly calculate rewrites based on input vs output (Audit requirement)
            merged_report = report_init # Start with copy
            merged_report.blocked_terms_found.extend(report_clip.blocked_terms_found)
            
            # Strict Audit: rewrite is true ONLY if strings changed
            has_changes = (clean_init != raw_init) or (clean_clip != raw_clip)
            merged_report.rewrites_applied = has_changes
            
            # Create Row
            row = PromptRow(
                beat_id=beat.beat_id,
                prompt_init_frame=clean_init,
                prompt_clip=clean_clip,
                negative_prompt=NEGATIVE_PROMPT_DEFAULT,
                sanitizer_report=merged_report
            )
            prompts.append(row)
            
        return PromptPack(run_id=self.run_id, prompts=prompts)
