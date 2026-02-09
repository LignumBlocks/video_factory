import os
import sys
import uuid
import shutil
from datetime import datetime
from typing import Optional

from src.foundation.config_loader import AppConfig
from src.foundation.validators import validate_input_files
from src.foundation.hashing import hash_file_sha256
from src.foundation.manifest import (
    RunManifest, 
    ManifestStatus,
    ManifestInputs,
    ManifestConfigEntry, 
    Phase,
    State,
    write_run_manifest, 
    load_run_manifest,
    write_phase_checkpoint,
    validate_consistency
)
from src.database_manager import DatabaseManager
from src.planning.models import BeatSheetRow, ClipPlanRow

# Order of execution
PHASE_ORDER = [
    Phase.INGEST,
    Phase.PLANNING,
    Phase.PROMPTS,
    Phase.FRAMES,
    Phase.CLIPS,
    Phase.ASSEMBLY
]

class RunOrchestrator:
    def __init__(self, run_id: str = None, video_id: str = "VID_001", project_id: str = "PROJ_FIN"):
        self.config = AppConfig.load()
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.video_id = video_id
        self.project_id = project_id
        
        # Setup run directory in artifacts
        self.run_dir = os.path.join(self.config.paths.artifacts_root, self.run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        
        # Initialize DB Logic
        self.db_manager = DatabaseManager("pipeline.db") # Default path
        self.db_manager.register_run(self.run_id, 1, self.video_id) # Ensure run exists in DB
        
        self.manifest: Optional[RunManifest] = None
        
        # Try to load existing manifest to resume
        try:
            self.manifest = load_run_manifest(self.run_id, self.config.paths.artifacts_root)
            validate_consistency(self.run_id, self.manifest, self.config.paths.artifacts_root)
            print(f"Orchestrator Resumed: RunID={self.run_id}, Phase={self.manifest.status.phase}, State={self.manifest.status.state}")
        except FileNotFoundError:
            print(f"Orchestrator Initialized: RunID={self.run_id} (New Run)")
        except RuntimeError as e:
            print(f"FATAL: Manifest Inconsistency: {e}")
            sys.exit(1)

    def initialize_run(self, script_path: str, audio_path: str, bible_path: str):
        """
        Explicit initialization step (INGEST logic effectively starts here).
        Creates the manifest relative to Phase.INGEST.
        """
        print(f"--- Initializing Run {self.run_id} ---")
        
        # 1. Validate
        validate_input_files(script_path, audio_path, bible_path)
        
        # 2. Hash Inputs
        script_hash = hash_file_sha256(script_path)
        audio_hash = hash_file_sha256(audio_path)
        bible_hash = hash_file_sha256(bible_path)
        
        # 3. Create Manifest
        now = datetime.utcnow().isoformat() + "Z"
        
        input_paths = {
            "script": script_path,
            "audio": audio_path,
            "bible": bible_path
        }
        
        # Copy to Frozen paths logic (prepare structure)
        frozen_paths = {
            "script": os.path.join(self.run_dir, "inputs/script.txt"),
            "audio": os.path.join(self.run_dir, "inputs/voiceover.mp3"),
            "bible": os.path.join(self.run_dir, "inputs/bible.md")
        }
        
        self.manifest = RunManifest(
            run_id=self.run_id,
            created_at=now,
            updated_at=now,
            status=ManifestStatus(phase=Phase.INGEST, state=State.NOT_STARTED),
            inputs=ManifestInputs(
                paths=input_paths,
                hashes={
                    "script": script_hash,
                    "audio": audio_hash,
                    "bible": bible_hash
                },
                frozen_paths=frozen_paths
            ),
            config_snapshot=ManifestConfigEntry(
                veo_duration=self.config.params.veo_duration_seconds,
                max_rerenders=self.config.params.max_rerenders
            ),
            artifacts_dir=self.run_dir
        )
        
        write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)
        
        # Freeze inputs now
        inputs_dir = os.path.join(self.run_dir, "inputs")
        os.makedirs(inputs_dir, exist_ok=True)
        shutil.copy(script_path, frozen_paths["script"])
        shutil.copy(audio_path, frozen_paths["audio"])
        shutil.copy(bible_path, frozen_paths["bible"])
        
        print("Run Initialized and Inputs Frozen.")
        
        # 4. Mark Ingest as Complete and advance to Planning
        self._mark_phase_complete(Phase.INGEST)

    def execute_stage(self, stage_name: str):
        """
        Public API for execution from Server/CLI.
        Maps string stage name to strict Phase enum and executes.
        """
        try:
            # Normalize string (INGEST -> Phase.INGEST)
            # We map "ingest" -> Phase.INGEST, "planning" -> Phase.PLANNING
            phase = Phase(stage_name.upper())
            self._execute_phase_wrapper(phase)
        except ValueError:
            print(f"WARNING: Unknown stage '{stage_name}'. Ignoring.")
            # Or raise to let server handle 400
            raise ValueError(f"Invalid stage name: {stage_name}")

    def run(self):
        """
        Main State Machine Loop.
        Iterates through phases defined in PHASE_ORDER.
        """
        if not self.manifest:
            raise RuntimeError("Run not initialized. Call initialize_run() first.")

        for phase in PHASE_ORDER:
            self._execute_phase_wrapper(phase)
            
            # If failed, stop immediately
            if self.manifest.status.state == State.FAILED:
                print(f"Run Halted at Phase {phase} due to Failure.")
                break

    def _execute_phase_wrapper(self, phase: Phase):
        """
        Generic state engine for checking, executing, and advancing phases.
        """
        # 1. Check if already done
        if phase in self.manifest.completed_phases:
            print(f"[SKIP] Phase {phase} already completed.")
            return

        # 2. Update Status to IN_PROGRESS
        print(f"--- Starting Phase: {phase} ---")
        self.manifest.status.phase = phase
        self.manifest.status.state = State.IN_PROGRESS
        write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)

        # 3. Execute
        try:
            if phase == Phase.INGEST:
                self._phase_ingest()
            elif phase == Phase.PLANNING:
                self._phase_planning()
            elif phase == Phase.PROMPTS:
                self._phase_prompts()
            elif phase == Phase.FRAMES:
                # TODO: Implement in future epic
                pass
            elif phase == Phase.CLIPS:
                pass
            elif phase == Phase.ASSEMBLY:
                pass
            
            # 4. Success -> Mark Done, Advance
            self._mark_phase_complete(phase)
            
        except Exception as e:
            # 5. Failure
            print(f"ERROR in {phase}: {e}")
            self.manifest.status.state = State.FAILED
            self.manifest.errors.append(str(e))
            write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)
            raise e # Re-raise to stop orchestration loop if calling from external script or debug

    def _mark_phase_complete(self, phase: Phase):
        # 1. Write Checkpoint
        write_phase_checkpoint(self.run_id, phase.value, self.config.paths.artifacts_root)
        
        # 2. Update Manifest
        self.manifest.completed_phases.append(phase)
        
        # Determine next phase
        try:
            current_index = PHASE_ORDER.index(phase)
            next_phase = PHASE_ORDER[current_index + 1]
            self.manifest.status.phase = next_phase
            self.manifest.status.state = State.NOT_STARTED
        except IndexError:
            # Last phase
            self.manifest.status.state = State.DONE
            
        write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)
        print(f"Phase {phase} COMPLETED. Next: {self.manifest.status.phase}")

    # --- Phase Implementations ---

    def _phase_ingest(self):
        # Ingest is mostly handled in initialize_run, but we might do extra checks here
        # or if we want to support strict separation where initialize prepares params 
        # and _phase_ingest validates them.
        # For now, since initialize_run freezes inputs, we just confirm logic here.
        print("Ingest logic executing...")
        # (Inputs already validated and frozen in initialize_run)

    def _phase_planning(self):
        script_path = self.manifest.inputs.frozen_paths["script"]
        audio_path = self.manifest.inputs.frozen_paths["audio"]
        
        with open(script_path, "r", encoding='utf-8') as f:
            script_text = f.read()

        from src.planning.planner import BeatPlanner
        from src.planning.validators import validate_scarcity, validate_clip_plan_integrity
        from src.audio_engine import AudioAligner
        
        # Audio Alignment
        print("Running Audio Alignment...")
        aligner = AudioAligner()
        alignment_segments, align_stats = aligner.align(script_path, audio_path)
        
        # Beat Planning
        planner = BeatPlanner()
        print("Running BeatPlanner...")
        beats = planner.plan_beats(script_text)
        
        # Merge Timings
        for i, beat in enumerate(beats):
            if i < len(alignment_segments):
                seg = alignment_segments[i]
                object.__setattr__(beat, '_temp_timing', seg)
            else:
                setattr(beat, '_temp_timing', {"start": 0.0, "end": 4.0})
        
        print(f"Generated {len(beats)} beats.")
        
        # Clip Planning
        print("Assigning Clip Plans...")
        clip_plans = planner.assign_clip_plans(beats)
        
        # Validate
        validate_scarcity(beats)
        validate_clip_plan_integrity(beats, clip_plans)
        
        # Write Artifacts
        beat_path = os.path.join(self.run_dir, "beat_sheet.jsonl")
        clip_path = os.path.join(self.run_dir, "clip_plan.jsonl")
        
        with open(beat_path, "w", encoding='utf-8') as f:
            for b in beats:
                f.write(b.model_dump_json() + "\n")
                
        with open(clip_path, "w", encoding='utf-8') as f:
            for c in clip_plans:
                f.write(c.model_dump_json() + "\n")
        
        # Sync to DB
        self._sync_planning_to_db(beats, clip_plans, align_stats)

    def _phase_prompts(self):
        beat_path = os.path.join(self.run_dir, "beat_sheet.jsonl")
        clip_path = os.path.join(self.run_dir, "clip_plan.jsonl")
        
        beats = []
        with open(beat_path, 'r') as f:
            for line in f:
                beats.append(BeatSheetRow.model_validate_json(line))
        
        clips = []
        with open(clip_path, 'r') as f:
            for line in f:
                clips.append(ClipPlanRow.model_validate_json(line))
                
        from src.prompts.generator import PromptGenerator
        generator = PromptGenerator(self.run_id)
        
        print(f"Generating Prompts for {len(beats)} beats...")
        pack = generator.generate_prompts(beats, clips)
        
        # STRICT CONTRACT: prompt_pack.jsonl
        prompts_path = os.path.join(self.run_dir, "prompt_pack.jsonl")
        
        with open(prompts_path, "w", encoding='utf-8') as f:
            for p in pack.prompts:
                f.write(p.model_dump_json() + "\n")
                
        self._sync_prompts_to_db(pack.prompts, prompts_path)  
          
    # --- DB Helpers ---
    
    def _sync_planning_to_db(self, beats, clip_plans, align_stats):
        print("Syncing Planning to DB...")
        beat_map = {b.beat_id: b for b in beats}
        for clip in clip_plans:
            beat = beat_map.get(clip.beat_id)
            if beat:
                timing = getattr(beat, '_temp_timing', {"start": 0.0, "end": 4.0})
                duration = timing['end'] - timing['start']
                shot_spec = {
                    "id": f"{self.run_id}_{beat.beat_id}",
                    "shot_id": f"{self.run_id}_{beat.beat_id}",
                    "run_id": self.run_id,
                    "version": 1,
                    "script_text": beat.vo_summary,
                    "intent": clip.action_intent,
                    "metaphor": f"[{beat.verb.value}] {beat.layer.value} - {clip.action_intent_category.value}",
                    "status": "PLANNED",
                    "duration_s": duration,
                    "beat_start_s": timing['start'], 
                    "beat_end_s": timing['end'],
                    "alignment_source": align_stats.source
                }
                self.db_manager.register_shot(shot_spec)
        self.db_manager.update_run_status(self.run_id, 1, "PLANNING", "done")

    def _sync_prompts_to_db(self, prompts, prompts_path):
        print("Syncing Prompts to DB...")
        for p in prompts:
            shot_id = f"{self.run_id}_{p.beat_id}"
            # Register Init Prompt (Role: image_prompt)
            self.db_manager.register_asset(
                shot_id=shot_id,
                asset_type="PROMPT",
                role="image_prompt",
                path=prompts_path,
                url=None,
                meta={"text": p.prompt_init_frame, "sanitized": p.sanitizer_report.rewrites_applied}
            )
            # Register Clip Prompt (Role: video_prompt)
            self.db_manager.register_asset(
                shot_id=shot_id,
                asset_type="PROMPT",
                role="video_prompt",
                path=prompts_path,
                url=None,
                meta={"text": p.prompt_clip, "sanitized": p.sanitizer_report.rewrites_applied}
            )
        self.db_manager.update_run_status(self.run_id, 1, "PROMPTS", "done")

# Legacy Pipeline wrapper is removed as per cleanup logic, 
# or kept minimal if strictly needed (but we are replacing core logic).
class Pipeline:
    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("Pipeline class is deprecated. Use RunOrchestrator.")
