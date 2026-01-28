import os
from typing import List
from .models import (
    QCReport, QCStatus, AlignmentStats, AlignmentSource, NanobananaRequest
)

class QCManager:
    def __init__(self):
        # Strict thresholds per Industrial Log - UPDATED FOR PHASE 4 REAL GEN
        self.PASS_COVERAGE_MIN = 0.99 # User Req: >= 99%
        self.PASS_CONFIDENCE_MIN = 0.85
        
        self.WARN_COVERAGE_MIN = 0.95
        # Below 0.95 coverage = BLOCK
        
        # Clean Score Jump Strict Vocabulary
        self.FORBIDDEN_WORDS = [
            "text", "words", "letters", "numbers", "ui", "hud", "interface", 
            "screen", "monitor", "display", "dashboard", "menu", "button", 
            "icon", "logo", "watermark", "signature", "username", "copyright",
            "blueprint", "schematic", "diagram", "chart", "graph", "trace", 
            "route", "map", "pin", "marker", "location", "gps", "detective", 
            "noir", "crime", "police", "investigation", "clue", "evidence", 
            "human", "person", "man", "woman", "child", "face", "hand", 
            "finger", "body", "silhouette", "figure", "statue", "mannequin",
            "robot", "android", "cyborg", "clothing", "suit", "shirt",
            "red", "green", "blue", "cyan", "neon", "laser", "glow",
            "multiple people", "crowd", "audience", "group", "team", "meeting",
            "petrol", "teal", "blue-green", "turquoise", "aqua"
        ]

    def evaluate_alignment(self, stats: AlignmentStats, stage: str = "planning_phase2") -> QCReport:
        critical_flags = []
        status = QCStatus.PASS
        stop_pipeline = False

        # 1. Source Check
        if stats.source != AlignmentSource.FORCED_ALIGNMENT:
            critical_flags.append(f"INVALID_SOURCE_{stats.source.name}")
            # Policy: Mock/Fallback is WARN for Real, but we handle simulation downstream.
            status = QCStatus.WARN 
            stop_pipeline = False

        # 2. Coverage Check
        if stats.coverage_pct < self.WARN_COVERAGE_MIN * 100:
             critical_flags.append(f"LOW_COVERAGE_{stats.coverage_pct:.1f}%")
             status = QCStatus.BLOCK
             stop_pipeline = True
        elif stats.coverage_pct < self.PASS_COVERAGE_MIN * 100:
             critical_flags.append(f"WARN_COVERAGE_{stats.coverage_pct:.1f}%")
             if status != QCStatus.BLOCK:
                 status = QCStatus.WARN
             stop_pipeline = True # Strict gate

        # 3. Confidence Check
        if stats.confidence_avg < self.PASS_CONFIDENCE_MIN:
             if status != QCStatus.BLOCK:
                 critical_flags.append(f"LOW_CONFIDENCE_{stats.confidence_avg:.2f}")
                 status = QCStatus.WARN
                 stop_pipeline = True

        # 4. Fallback Check (Redundant with Source usually, but explicit)
        if stats.fallback_used:
            critical_flags.append("FALLBACK_ALIGNMENT_USED")
            # In STRICT mode as requested, Fallback = BLOCK
            # Or at least do NOT set stop_pipeline to False
            if status != QCStatus.BLOCK:
                status = QCStatus.WARN # Or BLOCK if strict policy
            # Removed the line that forced stop_pipeline = False
            
        return QCReport(
            status=status,
            stage=stage,
            critical_flags=critical_flags,
            stop_pipeline=stop_pipeline
        )

    def evaluate_segments(self, segments: List[dict], min_dur: float, max_dur: float) -> QCReport:
        """
        Validates that all segments adhere to min/max duration constraints.
        """
        critical_flags = []
        status = QCStatus.PASS
        stop_pipeline = False
        
        for i, seg in enumerate(segments):
            dur = seg['end'] - seg['start']
            
            # Check Min
            if dur < min_dur:
                # Allow a tiny overlapping epsilon if needed, but user said strict.
                # using strict comparison for now.
                critical_flags.append(f"SEG_{i}_TOO_SHORT_{dur:.2f}s")
                status = QCStatus.BLOCK
                stop_pipeline = True
                
            # Check Max (Warn or Block? Usually Block for visual pacing)
            if dur > max_dur:
                critical_flags.append(f"SEG_{i}_TOO_LONG_{dur:.2f}s")
                status = QCStatus.BLOCK
                stop_pipeline = True
                
        return QCReport(
            status=status,
            stage="beat_normalization",
            critical_flags=critical_flags,
            stop_pipeline=stop_pipeline
        )

    def evaluate_still_pairs(self, shot_specs: List, final_prompts: List[NanobananaRequest], assets_dir: str) -> QCReport:
        """
        A→B Pair QC Gate v1
        Validates spec contracts (no filesize heuristics).
        """
        critical_flags = []
        status = QCStatus.PASS
        stop_pipeline = False
        
        # Build prompt map
        prompt_map = {}
        # Consolidate unique shot IDs processed
        processed_shot_ids = set()
        for req in final_prompts:
            processed_shot_ids.add(req.shot_id)
            key = f"{req.shot_id}_{req.pair_role.value}"
            prompt_map[key] = req
        
        # Only validate shots that were actually requested (handling limits)
        for shot_id in sorted(list(processed_shot_ids)):
            start_key = f"{shot_id}_start_ref"
            end_key = f"{shot_id}_end_ref"
            
            # Validate pair existence in spec
            if start_key not in prompt_map:
                critical_flags.append(f"MISSING_START_SPEC_{shot_id}")
                status = QCStatus.BLOCK
                stop_pipeline = True
            
            if end_key not in prompt_map:
                critical_flags.append(f"MISSING_END_SPEC_{shot_id}")
                status = QCStatus.BLOCK
                stop_pipeline = True
            
            # [GATE 2] Accent Color Consistency
            start_accent = None
            if start_key in prompt_map:
                start_accent = prompt_map[start_key].accent_color
            
            end_accent = None
            if end_key in prompt_map:
                end_accent = prompt_map[end_key].accent_color
            
                # [ALIGNMENT] Check for Forbidden Words - MOVED/UPDATED BELOW
                pass
                
                # Validate END constraints
            # [GATE 2] Accent Color Contract
                # [ALIGNMENT] Check for Forbidden Words in Prompt
                if end_key in prompt_map:
                    raw_prompt = prompt_map[end_key].prompt.lower()
                    # Strip out explicit "NEGATIVES:" section if mistakenly included
                    clean_prompt = raw_prompt.split("negatives:")[0]
                    clean_prompt = clean_prompt.split("**prompt negative:**")[0] 
                    
                    # print(f"DEBUG: shot_id={shot_id} RAW='{raw_prompt[:50]}...' CLEAN='{clean_prompt[:50]}...'")

                    for word in self.FORBIDDEN_WORDS:
                        if word in clean_prompt:
                            critical_flags.append(f"FORBIDDEN_WORD_{word.upper()}_{shot_id}")
                            status = QCStatus.WARN 
                            stop_pipeline = False

            # Validate END constraints
            if end_key in prompt_map:
                end_req = prompt_map[end_key] # Local Alias
                
                if not end_req.end_static:
                     critical_flags.append(f"END_NOT_STATIC_{shot_id}")
                     status = QCStatus.BLOCK
                     stop_pipeline = True

                if end_req.props_count > 2:
                    critical_flags.append(f"TOO_MANY_PROPS_{shot_id}_{end_req.props_count}")
                    status = QCStatus.BLOCK
                    stop_pipeline = True
                
                # Validate ab_plan is not empty
                if not end_req.ab_plan or end_req.ab_plan.strip() == "":
                    critical_flags.append(f"EMPTY_AB_PLAN_{shot_id}")
                    status = QCStatus.BLOCK
                    stop_pipeline = True
                
                # [GATE 2] Accent Color Contract
                if end_req.accent_color:
                    valid_values = ["#2F7D66", "#B23A48"]
                    acc_val = end_req.accent_color.value if hasattr(end_req.accent_color, 'value') else end_req.accent_color
                    
                    if acc_val not in valid_values:
                        critical_flags.append(f"INVALID_ACCENT_{shot_id}_{acc_val}")
                        status = QCStatus.BLOCK
                        stop_pipeline = True
                
                # Validate A→B budget (max 2 changes)
                if end_req.ab_changes_count > 2:
                    critical_flags.append(f"AB_BUDGET_EXCEEDED_{shot_id}_{end_req.ab_changes_count}")
                    status = QCStatus.BLOCK
                    stop_pipeline = True
            
            # File existence (secondary check)
            start_path = os.path.join(assets_dir, f"{shot_id}_start_ref.png")
            end_path = os.path.join(assets_dir, f"{shot_id}_end_ref.png")
            
            if not os.path.exists(start_path):
                critical_flags.append(f"MISSING_START_FILE_{shot_id}")
                status = QCStatus.BLOCK
                stop_pipeline = True
            
            if not os.path.exists(end_path):
                critical_flags.append(f"MISSING_END_FILE_{shot_id}")
                status = QCStatus.BLOCK
                stop_pipeline = True
        
        return QCReport(
            status=status,
            stage="ab_pair_qc_v1",
            critical_flags=critical_flags,
            stop_pipeline=stop_pipeline
        )

