import hashlib
import os
from typing import List, Dict
from .models import (
    ShotSpec, NanobananaRequest, VeoRequest, 
    AlignmentSource, CameraSpec, ContinuitySpec,
    CameraMovement, ShotSize, CameraAngle, PairRole, AccentColor,
    AlignmentStats
)
from .clients.agent import AgentClient

class VisualDirector:
    def __init__(self, global_config, style_bible_content: str = ""):
        self.config = global_config
        self.style_bible = style_bible_content
        self.agent = AgentClient()

    def _generate_shot_id(self, run_id: str, index: int) -> str:
        return f"{run_id}_s{index:03d}"

    def _generate_beat_id(self, run_id: str, index: int) -> str:
        return f"{run_id}_b{index:03d}"

    def _generate_request_id(self, run_id: str, shot_id: str, suffix: str) -> str:
        return f"req_{run_id}_{shot_id}_{suffix}"

    def _derive_visual_intent(self, text: str) -> Dict[str, str]:
        """
        Derive visual intent using Agent (LLM) if available, otherwise fallback to heuristics.
        """
        # Try Agent First
        agent_suggestion = self.agent.suggest_visuals(text)
        if agent_suggestion:
            # Normalize camera string to Enum if possible
            cam_str = agent_suggestion.get("camera", "STATIC").upper()
            try:
                # Validate enum
                valid_cam = CameraMovement(cam_str)
            except ValueError:
                valid_cam = CameraMovement.STATIC
            
            return {
                "metaphor": agent_suggestion.get("metaphor", "Abstract finance scene"),
                "camera": valid_cam,
                "intent": agent_suggestion.get("intent", f"Visualize: {text[:20]}...")
            }

        # Fallback Heuristic
        text_lower = text.lower()
        metaphor = "Abstract minimal finance shapes"
        camera_move = CameraMovement.STATIC
        
        if "increase" in text_lower or "growth" in text_lower:
            metaphor = "Green arrow moving upwards on a graph"
            camera_move = CameraMovement.TILT_UP
        elif "risk" in text_lower or "danger" in text_lower:
            metaphor = "Red warning triangular signs floating"
            camera_move = CameraMovement.ZOOM_IN
        elif "data" in text_lower:
            metaphor = "Digital grid of numbers glowing"
            camera_move = CameraMovement.PAN_RIGHT
            
        return {
            "metaphor": metaphor,
            "camera": camera_move,
            "intent": "Fallback: " + text[:20]
        }
    
    def _compute_constraints(self, metaphor: str, script_text: str, camera: CameraMovement, is_start: bool) -> dict:
        """
        Deterministically compute props_count, ab_changes_count, accent_color from metaphor/script.
        v0: Simple pattern matching (no NLP/vision).
        """
        metaphor_lower = metaphor.lower()
        script_lower = script_text.lower()
        
        # Count props by identifying common objects in metaphor
        prop_keywords = ["arrow", "sign", "graph", "chart", "barrier", "gate", "coin", "document", "key", "lock"]
        props_count = sum(1 for keyword in prop_keywords if keyword in metaphor_lower)
        props_count = min(props_count, 2)  # Cap at 2 per style bible
        
        # Compute ab_changes_count based on camera complexity + action words
        ab_changes_count = 1  # Default: single transform
        
        # Complex movements suggest multiple changes
        if camera in [CameraMovement.ZOOM_IN, CameraMovement.ZOOM_OUT]:
            ab_changes_count += 1
        
        # Action verbs in script suggest transformations
        action_words = ["remove", "break", "open", "unlock", "transform", "increase", "decrease"]
        if any(word in script_lower for word in action_words):
            ab_changes_count = min(ab_changes_count + 1, 2)
        
        # Determine accent_color from sentiment
        negative_keywords = ["risk", "danger", "problem", "issue", "barrier", "block", "friction", "loss", "decline"]
        positive_keywords = ["growth", "increase", "success", "solution", "opportunity", "gain", "improve", "rise"]
        
        accent_color = None
        if is_start:
            # START frame: show problem/setup
            if any(word in script_lower for word in negative_keywords):
                accent_color = AccentColor.NEGATIVE
            elif any(word in script_lower for word in positive_keywords):
                accent_color = AccentColor.POSITIVE
        else:
            # END frame: show resolution/result
            if any(word in script_lower for word in positive_keywords):
                accent_color = AccentColor.POSITIVE
            elif any(word in script_lower for word in negative_keywords):
                accent_color = AccentColor.NEGATIVE
        
        return {
            "props_count": props_count,
            "ab_changes_count": ab_changes_count,
            "accent_color": accent_color
        }

    def _extract_block_id(self, text: str) -> str:
        """Extracts Bxx from text headers if present, else defaults."""
        import re
        match = re.search(r"(B\d+)", text)
        return match.group(1) if match else "B00"

    def _infer_dramatic_role(self, text: str) -> str:
        """Simple keyword heuristic for dramatic role."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["problem", "fail", "error", "loss"]): return "problem"
        if any(w in text_lower for w in ["but", "however", "wait"]): return "friction"
        if any(w in text_lower for w in ["solution", "fix", "success", "gain"]): return "result"
        return "setup"

    def create_plan(self, aligned_segments: List[Dict], align_stats: AlignmentStats) -> dict:
        shots: List[ShotSpec] = []
        nano_requests: List[NanobananaRequest] = []
        veo_requests: List[VeoRequest] = []
        
        print(f"Creating visual plan for {len(aligned_segments)} segments...")
        for i, seg in enumerate(aligned_segments):
            print(f"[{i+1}/{len(aligned_segments)}] Processing segment: {seg['text'][:50]}...")
            shot_id = self._generate_shot_id(self.config.run_id, i+1)
            beat_id = self._generate_beat_id(self.config.run_id, i+1)
            
            # 1. Visual Intent
            intent_data = self._derive_visual_intent(seg['text'])
            print(f"[{i+1}/{len(aligned_segments)}] ✓ Generated visual intent for {shot_id}")
            
            # Update progress in database
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.update_stage_progress(
                    self.config.run_id, 
                    self.config.version, 
                    i + 1, 
                    len(aligned_segments),
                    f"Processing segment {i+1}/{len(aligned_segments)}"
                )
            
            # 2. Build ShotSpec
            camera_spec = CameraSpec(
                movement=intent_data['camera'],
                shot_size=ShotSize.MEDIUM, 
                angle=CameraAngle.EYE_LEVEL,
                strength=0.5
            )
            
            shot = ShotSpec(
                id=shot_id,
                beat_id=beat_id,
                run_id=self.config.run_id,
                video_id=self.config.video_id,
                beat_start_s=seg['start'],
                beat_end_s=seg['end'],
                duration_s=seg['end'] - seg['start'],
                script_text=seg['text'],
                metaphor=intent_data['metaphor'],
                intent=intent_data['intent'],
                phase_start_intent="Start of concept" if i == 0 else None,
                phase_end_intent="End of video" if i == len(aligned_segments)-1 else None,
                camera=camera_spec,
                continuity=ContinuitySpec(), # Empty for now
                seed=self.config.global_seed + i,
                alignment_source=align_stats.source,
                alignment_confidence=1.0 if align_stats.source == AlignmentSource.FORCED_ALIGNMENT else 0.8,
                # [GATE 1] Heuristic Metadata Population
                block_id=self._extract_block_id(seg['text']), 
                dramatic_role=self._infer_dramatic_role(seg['text'])
            )
            shots.append(shot)
            
            # 3. Build Nanobanana Requests (Start & End Refs)
            # Compute constraints deterministically
            start_constraints = self._compute_constraints(
                metaphor=intent_data['metaphor'],
                script_text=seg['text'],
                camera=intent_data['camera'],
                is_start=True
            )
            
            # Determine prompt based on ALIGNMENT_MODE for start ref
            if os.environ.get("ALIGNMENT_MODE") == "CLEAN_SCORE":
                start_prompt = f"Visual: {intent_data['metaphor']}, abstract minimal flat vector editorial"
                start_negative_prompt = "multiple people, ears, facial features, petrol, teal, blue-green, text, UI elements, clutter, >2 props"
            else:
                start_prompt = f"{intent_data['metaphor']}"
                start_negative_prompt = "multiple people, ears, facial features, petrol, teal, blue-green, text, UI elements, clutter, >2 props"
            
            # Start Ref
            nano_req_start = NanobananaRequest(
                request_id=self._generate_request_id(self.config.run_id, shot_id, "img_start"),
                shot_id=shot_id,
                beat_id=beat_id,
                pair_role=PairRole.START_REF,
                end_static=False,
                props_count=start_constraints['props_count'],
                accent_color=start_constraints['accent_color'],
                ab_plan=f"Pre-action: {intent_data['metaphor']}",
                ab_changes_count=start_constraints['ab_changes_count'],
                prompt=start_prompt,
                style_bible_hash=self.config.style_bible_hash,
                negative_prompt=start_negative_prompt,
                seed=shot.seed,
                aspect_ratio="16:9"
            )
            nano_requests.append(nano_req_start)
            
            
            # Compute END constraints
            end_constraints = self._compute_constraints(
                metaphor=intent_data['metaphor'],
                script_text=seg['text'],
                camera=intent_data['camera'],
                is_start=False
            )

            # Determine prompt based on ALIGNMENT_MODE for end ref
            if os.environ.get("ALIGNMENT_MODE") == "CLEAN_SCORE":
                end_prompt = "abstract minimal flat vector editorial"
                end_negative_prompt = "multiple people, ears, facial features, petrol, teal, blue-green, text, UI elements, clutter, >2 props, motion blur, movement, specific objects, detailed scenes"
            else:
                end_prompt = f"{intent_data['metaphor']}, minimal flat vector editorial"
                end_negative_prompt = "multiple people, ears, facial features, petrol, teal, blue-green, text, UI elements, clutter, >2 props, motion blur, movement"
            
            # End Ref
            nano_req_end = NanobananaRequest(
                request_id=self._generate_request_id(self.config.run_id, shot_id, "img_end"),
                shot_id=shot_id,
                beat_id=beat_id,
                pair_role=PairRole.END_REF,
                end_static=True,
                props_count=end_constraints['props_count'],
                accent_color=end_constraints['accent_color'],
                ab_plan=f"Post-action: result visible, fully static",
                ab_changes_count=end_constraints['ab_changes_count'],
                prompt=f"{intent_data['metaphor']}, minimal flat vector editorial",
                style_bible_hash=self.config.style_bible_hash,
                negative_prompt="multiple people, ears, facial features, petrol, teal, blue-green, text, UI elements, clutter, >2 props, motion blur, movement",
                seed=shot.seed,
                aspect_ratio="16:9"
            )
            nano_requests.append(nano_req_end)
            
            # 4. Build Veo Request
            veo_req = VeoRequest(
                request_id=self._generate_request_id(self.config.run_id, shot_id, "veo"),
                shot_id=shot_id,
                beat_id=beat_id,
                prompt=f"{intent_data['metaphor']}, {intent_data['camera'].value} movement",
                duration_s=shot.duration_s,
                fps=self.config.fps,
                seeds=shot.seed if 10000 <= shot.seed <= 99999 else None,  # Validar rango
                aspect_ratio="16:9",
                style_profile_id=self.config.style_bible_hash,
                negative_profile_id="cluttered, distortion, morphing",
                image_ref_start=None, # Will be populated in Phase 2/3 ideally, or linked by ID now
                image_ref_end=None
            )
            veo_requests.append(veo_req)

        return {
            "shots": shots,
            "nano_requests": nano_requests,
            "veo_requests": veo_requests
        }
