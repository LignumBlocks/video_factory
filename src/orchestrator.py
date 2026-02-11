import os
import sys
import uuid
import shutil
import subprocess
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

from src.foundation.config_loader import AppConfig
from src.foundation.validators import validate_input_files
from src.foundation.hashing import hash_file_sha256
from src.foundation.manifest import (
    RunManifest, 
    ManifestApp,
    ManifestPaths,
    ManifestInputs,
    InputFileMeta,
    AudioInputMeta,
    BibleInputMeta,
    ManifestStep,
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
        self.video_id = video_id
        self.project_id = project_id
        self.db_manager = DatabaseManager("pipeline.db") # Default path
        
        self.manifest: Optional[RunManifest] = None

        if run_id:
            # RESUME MODE
            self.run_id = run_id
            self.run_dir = os.path.join(self.config.paths.artifacts_root, self.run_id)
            try:
                self._setup_run_logger()
            except Exception as e:
                logger.warning(f"Could not setup run logger: {e}")
            
            # Try to load manifest
            try:
                self.manifest = load_run_manifest(self.run_id, self.config.paths.artifacts_root)
                validate_consistency(self.run_id, self.manifest, self.config.paths.artifacts_root)
                logger.info(f"Orchestrator Resumed: RunID={self.run_id}, Status={self.manifest.status}")
            except FileNotFoundError:
                 # If run_id passed but not found, maybe invalid? Or just starting manually with ID?
                 # Assuming valid resume.
                 logger.warning(f"RunID {self.run_id} provided but manifest not found.")
            except RuntimeError as e:
                logger.critical(f"FATAL: Manifest Inconsistency: {e}")
                sys.exit(1)
        else:
            # NEW RUN MODE (Deferred initialization)
            self.run_id = None
            self.run_dir = None
            logger.info("Orchestrator instantiated for New Run (waiting for initialize_run).")

    def initialize_run(self, script_path: str, audio_path: str, bible_path: str):
        """
        Explicit initialization step (INGEST logic effectively starts here).
        Creates the manifest relative to Phase.INGEST.
        """
        logger.info(f"--- Initializing New Run ---")
        
        # 1. Validate (Using refactored Preflight Validator)
        logger.info("Running Preflight Validation...")
        report = validate_input_files(script_path, audio_path, bible_path)
        is_valid = report["passed"]
        
        # 2. Hash Inputs (Required for ID generation)
        script_hash = "00000000"
        audio_hash = "00000000"
        bible_hash = "00000000"
        
        if os.path.exists(script_path): script_hash = hash_file_sha256(script_path)
        if os.path.exists(audio_path): audio_hash = hash_file_sha256(audio_path)
        if os.path.exists(bible_path): bible_hash = hash_file_sha256(bible_path)
        
        # 3. Generate Deterministic RUN ID
        combined_hash = hash_file_sha256(None, data=(script_hash + audio_hash + bible_hash).encode('utf-8'))
        short_hash = combined_hash[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        new_run_id = f"{timestamp}_{short_hash}"
        
        # Set Identity
        self.run_id = new_run_id
        logger.info(f"Initialized New Run ID: {self.run_id}")
        self.run_dir = os.path.join(self.config.paths.artifacts_root, self.run_id)
        
        # Register in DB
        self.db_manager.register_run(self.run_id, 1, self.video_id)
        
        # 4. Create Directory Structure
        logger.info(f"Creating Run Directory: {self.run_dir}")
        os.makedirs(self.run_dir, exist_ok=True)
        
        structure = [
            "inputs",
            "inputs/config",  # T-101: frozen configs
            "work/beats",
            "work/prompts",
            "work/frames",
            "work/clips",
            "work/qc",
            "work/assembly",
            "outputs",
            "logs"
        ]
        
        for folder in structure:
            os.makedirs(os.path.join(self.run_dir, folder), exist_ok=True)
            
        self._setup_run_logger()

        # T-101: Copy and freeze configs
        logger.info("Freezing Shot Menu and System Rules...")
        config_frozen_dir = os.path.join(self.run_dir, "inputs/config")
        
        # Source configs from repo
        shot_menu_source = "config/shot_menu.yaml"
        system_rules_source = "config/system_rules.yaml"
        
        # Destination in run
        shot_menu_dest = os.path.join(config_frozen_dir, "shot_menu.yaml")
        system_rules_dest = os.path.join(config_frozen_dir, "system_rules.yaml")
        
        # Copy configs
        if not os.path.exists(shot_menu_source):
            logger.warning(f"Shot Menu not found at {shot_menu_source}, skipping config freeze.")
            config_meta = None
        elif not os.path.exists(system_rules_source):
            logger.warning(f"System Rules not found at {system_rules_source}, skipping config freeze.")
            config_meta = None
        else:
            shutil.copy(shot_menu_source, shot_menu_dest)
            shutil.copy(system_rules_source, system_rules_dest)
            
            # Hash frozen configs (hash_file_sha256 already imported at top)
            from src.config.loader import load_shot_menu
            
            shot_menu_hash = hash_file_sha256(shot_menu_dest)
            system_rules_hash = hash_file_sha256(system_rules_dest)
            
            # Load to extract menu_id
            try:
                shot_menu_config = load_shot_menu(shot_menu_dest)
                menu_id = shot_menu_config.menu_id
                config_schema_version = shot_menu_config.schema_version
            except Exception as e:
                logger.error(f"Failed to load frozen shot menu: {e}")
                menu_id = "unknown"
                config_schema_version = "1.0"
            
            from src.foundation.manifest import ManifestConfigMeta
            config_meta = ManifestConfigMeta(
                shot_menu_sha256=shot_menu_hash,
                system_rules_sha256=system_rules_hash,
                menu_id=menu_id,
                schema_version=config_schema_version
            )

        # 5. Populate Manifest Data (Metadata Extraction)
        # We need size, duration, locked status
        script_size = os.path.getsize(script_path) if os.path.exists(script_path) else 0
        audio_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
        bible_size = os.path.getsize(bible_path) if os.path.exists(bible_path) else 0
        
        # Audio Duration
        audio_duration = 0.0
        if os.path.exists(audio_path):
            try:
                from mutagen.mp3 import MP3
                audio = MP3(audio_path)
                audio_duration = audio.info.length
            except: pass
            
        # Bible Locked
        bible_locked = False
        if os.path.exists(bible_path):
             with open(bible_path, 'r', encoding='utf-8') as f:
                  if "LOCKED" in f.read(4096): bible_locked = True

        # Frozen paths
        frozen_paths = {
            "script": os.path.join(self.run_dir, "inputs/script.txt"),
            "audio": os.path.join(self.run_dir, "inputs/voiceover.mp3"),
            "style_bible": os.path.join(self.run_dir, "inputs/style_bible_LOCKED.md")
        }
        
        # 6. Create Manifest Object (V1)
        # Git Commit
        try:
            git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
        except Exception:
            git_commit = "unknown"

        now_iso = datetime.utcnow().isoformat() + "Z"
        status_state = State.NOT_STARTED
        if not is_valid:
            status_state = State.FAILED_PREFLIGHT
            
        from src.foundation.manifest import (
            ManifestApp, ManifestPaths, ManifestInputs, 
            InputFileMeta, AudioInputMeta, BibleInputMeta, ManifestStep
        )

        manifest = RunManifest(
            schema_version="1.0",
            run_id=self.run_id,
            created_at=now_iso,
            status=status_state,
            app=ManifestApp(git_commit=git_commit),
            paths=ManifestPaths(
                run_root=self.run_dir,
                inputs_dir=os.path.join(self.run_dir, "inputs"),
                work_dir=os.path.join(self.run_dir, "work"),
                outputs_dir=os.path.join(self.run_dir, "outputs")
            ),
            inputs=ManifestInputs(
                script=InputFileMeta(
                    filename="script.txt",
                    sha256=script_hash,
                    bytes=script_size
                ),
                voiceover=AudioInputMeta(
                    filename="voiceover.mp3",
                    sha256=audio_hash,
                    bytes=audio_size,
                    duration_s=audio_duration
                ),
                style_bible=BibleInputMeta(
                    filename="style_bible_LOCKED.md",
                    sha256=bible_hash,
                    bytes=bible_size,
                    locked=bible_locked
                )
            ),
            config=config_meta  # T-101: frozen config metadata
        )
        
        # Add Preflight Step
        report["run_id"] = self.run_id
        step = ManifestStep(
            phase=Phase.INGEST, # Or create a specific PREFLIGHT phase? Sticking to INGEST for now or maybe PREFLIGHT if enum allows
            status=State.DONE if is_valid else State.FAILED,
            timestamp=now_iso,
            metadata={"report_file": "preflight_report.json"}
        )
        manifest.steps.append(step)
        
        self.manifest = manifest
        
        # Write Manifest
        write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)
        
        # Write Preflight Report
        report_path = os.path.join(self.run_dir, "preflight_report.json")
        with open(report_path, "w", encoding='utf-8') as f:
            json.dump(report, f, indent=2)
            
        if not is_valid:
            logger.error("PREFLIGHT FAILED. Run created in FAILED_PREFLIGHT state.")
            logger.error(f"Report written to {report_path}")
            return

        # 6. Copy Inputs (Frozen Paths)
        shutil.copy(script_path, frozen_paths["script"])
        shutil.copy(audio_path, frozen_paths["audio"])
        shutil.copy(bible_path, frozen_paths["style_bible"])
        
        # Write Checkpoint for INGEST (Preflight Done)
        write_phase_checkpoint(self.run_id, Phase.INGEST.value, self.config.paths.artifacts_root, report)
        
        logger.info("Run Initialized and Inputs Frozen.")
        # self._mark_phase_complete(Phase.INGEST) # Revert to using manifest steps? 
        # For now, let's keep marking complete if we use that logic, but V1 uses steps.
        # I will start using steps for logging.
        pass

    def _setup_run_logger(self):
        """
        Configures a run-specific FileHandler for logging.
        Writes to: <run_dir>/logs/run.log
        """
        if not self.run_dir: return

        log_path = os.path.join(self.run_dir, "logs", "run.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        # Remove previous handlers if any (to avoid duplicates)
        logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.FileHandler) or "run.log" not in h.baseFilename]
        
        handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [RunID:%(run_id)s] - %(message)s'
        )
        
        # We need to inject run_id into the log record. 
        # Using a Filter is better than hardcoding format string if run_id was dynamic, but here it's static per run.
        # But `logger` is a module-level logger, shared by all instances if we are not careful.
        # However, `videofactory` runs as a single process per run.
        # So we can just use a Filter or Adapter.
        
        class RunIdFilter(logging.Filter):
            def __init__(self, run_id):
                super().__init__()
                self.run_id = run_id
            def filter(self, record):
                record.run_id = self.run_id
                return True
                
        handler.setFormatter(formatter)
        handler.addFilter(RunIdFilter(self.run_id))
        
        logger.addHandler(handler)
        logger.info(f"Run Logger Configured: {log_path}")

    def _create_initial_manifest(self, *args, **kwargs):
        # Deprecated by inline logic above
        pass


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
            logger.warning(f"WARNING: Unknown stage '{stage_name}'. Ignoring.")
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
            if self.manifest.status == State.FAILED:
                logger.error(f"Run Halted at Phase {phase} due to Failure.")
                break

    def _execute_phase_wrapper(self, phase: Phase):
        """
        Generic state engine for checking, executing, and advancing phases.
        Refactored to use Step Runner (T-007).
        """
        completed_steps = [s.phase for s in self.manifest.steps if s.status == State.DONE]
        if phase in completed_steps:
            logger.info(f"[SKIP] Phase {phase} already completed.")
            return

        logger.info(f"--- Starting Phase: {phase} ---")
        
        # 1. Add Manifest Step (Tracking Start)
        manifest_step = ManifestStep(
            name=f"{phase.value}_EXECUTION", # Default name
            phase=phase,
            status=State.IN_PROGRESS,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        self.manifest.steps.append(manifest_step)
        self.manifest.status = State.IN_PROGRESS
        write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)

        # 2. Resolve Step Implementation
        from src.foundation.step_runner import StepContext
        from src.steps.definitions import IngestStep, PlanningStep, PromptsStep, PlaceholderStep
        
        context = StepContext(
            run_id=self.run_id,
            run_dir=self.run_dir,
            services={"db": self.db_manager},
            artifacts_root=self.config.paths.artifacts_root
        )
        
        step_impl = None
        if phase == Phase.INGEST:
            step_impl = IngestStep()
        elif phase == Phase.PLANNING:
            step_impl = PlanningStep()
        elif phase == Phase.PROMPTS:
            step_impl = PromptsStep()
        else:
            # Generic Placeholder for Frames, Clips, Assembly
            step_impl = PlaceholderStep(f"{phase.value}_GEN", phase)

        # 3. Execute Step
        try:
            # Update manifest step name based on implementation
            manifest_step.name = step_impl.name
            
            result = step_impl.run(context)
            
            if result.status == State.DONE:
                self._mark_phase_complete(phase)
            else:
                raise RuntimeError(f"Step {step_impl.name} failed with status {result.status}")
                
        except Exception as e:
            logger.error(f"ERROR in {phase}: {e}")
            self.manifest.status = State.FAILED
            for s in reversed(self.manifest.steps):
                if s.phase == phase:
                    s.status = State.FAILED
                    s.error = str(e)
                    break
            write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)
            raise e

    def _mark_phase_complete(self, phase: Phase):
        # 1. Write Checkpoint (Legacy compatibility if needed, keeping it for robustness)
        write_phase_checkpoint(self.run_id, phase.value, self.config.paths.artifacts_root)
        
        # 2. Update Manifest Steps
        updated = False
        for s in reversed(self.manifest.steps):
            if s.phase == phase and s.status == State.IN_PROGRESS:
                s.status = State.DONE
                s.timestamp = datetime.utcnow().isoformat() + "Z" # Update timestamp to completion time? Or keep start time and add completion time?
                # For simplicity, keeping original timestamp as start time, maybe?
                # Actually, reqs say: "timestamp": "...", "status": "DONE".
                # Let's update timestamp to completion time if we want to log when it finished.
                # Or add `ended_at` field later. For now just update status.
                updated = True
                break
        
        # If not found (e.g. initialize_run skip), add it?
        if not updated:
             # Add completed step if not present (e.g. initialize_run called directly without execute_wrapper)
             step = ManifestStep(
                phase=phase,
                status=State.DONE,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
             self.manifest.steps.append(step)

        # Determine next phase (Not strictly needed for logic, just for logging/status)
        current_index = PHASE_ORDER.index(phase)
        if current_index == len(PHASE_ORDER) - 1:
            self.manifest.status = State.DONE
        else:
            self.manifest.status = State.IN_PROGRESS # Continues...
            
        write_run_manifest(self.run_id, self.manifest, self.config.paths.artifacts_root)
        logger.info(f"Phase {phase} COMPLETED.")

    # --- Phase Implementations ---

    def _phase_ingest(self):
        # Ingest is mostly handled in initialize_run, but we might do extra checks here
        # or if we want to support strict separation where initialize prepares params 
        # and _phase_ingest validates them.
        # For now, since initialize_run freezes inputs, we just confirm logic here.
        logger.info("Ingest logic executing...")
        # (Inputs already validated and frozen in initialize_run)

    def _phase_planning(self):
        logger.info("--- PLACEHOLDER: Executing Planning Phase ---")
        # In a real run, this would align audio, plan beats, and assign clips.
        # For now, we simulate success and write dummy artifacts to satisfy consistency if needed.
        # But since next steps are also placeholders, we can just mark it done.
        
        # Simulate artifact creation for traceability
        beat_path = os.path.join(self.run_dir, "beat_sheet.jsonl")
        if not os.path.exists(beat_path):
            with open(beat_path, 'w') as f:
                f.write('{"beat_id": "B0001", "action_intent": "placeholder"}\n')
        
        clip_path = os.path.join(self.run_dir, "clip_plan.jsonl")
        if not os.path.exists(clip_path):
            with open(clip_path, 'w') as f:
                 f.write('{"beat_id": "B0001", "action_intent": "placeholder"}\n')
                 
        logger.info("Planning Phase Completed (Placeholder).")

    def _phase_prompts(self):
        logger.info("--- PLACEHOLDER: Executing Prompts Phase ---")
        prompts_path = os.path.join(self.run_dir, "prompt_pack.jsonl")
        if not os.path.exists(prompts_path):
            with open(prompts_path, 'w') as f:
                f.write('{"prompt_id": "P001", "prompt_text": "placeholder"}\n')
        logger.info("Prompts Phase Completed (Placeholder).")
        
    def _phase_frames(self):
        logger.info("--- PLACEHOLDER: Executing Frames Generation Phase ---")
        # TODO: Implement image generation logic
        logger.info("Frames Phase Completed (Placeholder).")

    def _phase_clips(self):
        logger.info("--- PLACEHOLDER: Executing Video Clips Phase ---")
        # TODO: Implement video generation logic
        logger.info("Clips Phase Completed (Placeholder).")

    def _phase_assembly(self):
        logger.info("--- PLACEHOLDER: Executing Final Assembly Phase ---")
        # TODO: Implement ffmpeg concatenation logic
        logger.info("Assembly Phase Completed (Placeholder).")  
          
    # --- DB Helpers ---
    
    def _sync_planning_to_db(self, beats, clip_plans, align_stats):
        logger.info("Syncing Planning to DB...")
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
        logger.info("Syncing Prompts to DB...")
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
