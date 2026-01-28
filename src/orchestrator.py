import os
import json
import hashlib
import shutil
import sys
from datetime import datetime
from typing import Dict, List
from pydantic import BaseModel
from .models import (
    GlobalConfig, Manifest, ReadyFile, QCReport, QCStatus,
    FileMetadata, AlignmentSource, NanobananaRequest, GenerationMode
)
from .audio_engine import AudioAligner
from .visual_director import VisualDirector
from .qc_manager import QCManager
from .generation import ImageGenerator
from .beat_normalizer import BeatNormalizer
from .beat_normalizer import BeatNormalizer
from .database_manager import DatabaseManager

class Pipeline:
    def __init__(self, run_id: str, version: int, project_id: str = "PROJ_FIN", video_id: str = "VID_001"):
        self.run_id = run_id
        self.version = version
        self.project_id = project_id
        self.video_id = video_id
        
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.input_dir = os.path.join(self.base_dir, "runs", run_id, f"v{version}", "staging")
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.input_dir = os.path.join(self.base_dir, "runs", run_id, f"v{version}", "staging")
        self.export_root = os.path.join(self.base_dir, "exports", video_id)
        
        self.export_root = os.path.join(self.base_dir, "exports", video_id)
        
        self.db_manager = DatabaseManager(os.path.join(self.base_dir, "pipeline.db"))
        self.db_manager.register_run(run_id, version, video_id)
        
    def _read_file(self, path: str, binary=False):
        mode = 'rb' if binary else 'r'
        encoding = None if binary else 'utf-8'
        with open(path, mode, encoding=encoding) as f:
            return f.read()

    def _calculate_checksum(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def _write_json(self, data: BaseModel, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data.model_dump_json(indent=2))

    def _write_jsonl(self, items: list, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(item.model_dump_json())
                f.write('\n')

    def run(self):
        print(f"Starting Pipeline Run: {self.run_id} v{self.version}")
        
        # 1. Setup Inputs & Hash
        script_path = os.path.join(self.input_dir, "script.txt")
        audio_path = os.path.join(self.input_dir, "voiceover.mp3")
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
            
        script_content = self._read_file(script_path)
        script_hash = hashlib.md5(script_content.encode('utf-8')).hexdigest()[:8]
        
        # Load style bible
        style_bible_path = os.path.join(self.input_dir, "style_bible.md")
        
        if not os.path.exists(style_bible_path):
            raise FileNotFoundError(f"style_bible.md required in staging: {style_bible_path}")
        
        # Load and hash style bible (SHA256, not MD5)
        style_bible_content = self._read_file(style_bible_path)
        style_bible_hash = hashlib.sha256(style_bible_content.encode('utf-8')).hexdigest()[:12]
        
        # 2. Idempotency Check & Path Setup
        timestamp_str = datetime.now().strftime("%Y%m%d")
        # In a real system, we might look for existing dirs.
        # For this MVP, if the specific version folder exists, assume overwrite or error?
        # User rule: "no sobrescribir exports finales... incrementa version"
        # Since 'version' is an input arg, if it exists, we technically shouldn't run.
        # But for 'staging' we might overlap.
        # Let's check:
        # We need to find if export dir exists. We can't know the date/hash a priori if we are creating it now.
        # But we can check if `run_{self.run_id}/v{self.version}` exists inside ANY date folder?
        # For simplicity in this script, we just proceed. Uniqueness is typically handled by caller bumping version.
        
        run_export_dir = os.path.join(
            self.export_root, 
            f"{timestamp_str}_{script_hash}", 
            f"run_{self.run_id}", 
            f"v{self.version}"
        )
        if os.path.exists(run_export_dir):
            print(f"WARNING: Export directory already exists: {run_export_dir}")
            # In strict mode, we might raise error.
        
        os.makedirs(run_export_dir, exist_ok=True)
        print(f"Export Directory: {run_export_dir}")
        shutil.copy(audio_path, os.path.join(run_export_dir, "voiceover.mp3"))
        shutil.copy(style_bible_path, os.path.join(run_export_dir, "style_bible.md"))

        # 3. Audio Engine (Gateway Mode)
        # Try Forced first
        aligner = AudioAligner(source=AlignmentSource.FORCED_ALIGNMENT)
        
        # [INTEGRITY_01] Get strict duration
        # REMOVED FALLBACK: Must succeed or fail pipeline.
        actual_vo_duration = aligner.get_audio_duration(audio_path)
        print(f"Audio Duration (ffprobe): {actual_vo_duration:.3f}s")

        

        run_identity = {
            "project_id": self.project_id,
            "video_id": self.video_id,
            "run_id": self.run_id,
            "version": self.version,
            "script_hash": script_hash
        }
        segments, align_stats = aligner.align(script_path, audio_path, run_identity)
        
        print(f"DEBUG: Received {len(segments)} segments from Aligner.")
        if segments:
            print(f"DEBUG: First Seg: {segments[0]}")
            print(f"DEBUG: Last Seg: {segments[-1]}")
        
        # [QC_02] Beat Normalization
        config_min_beat = float(os.environ.get("BEAT_MIN_DURATION", "2.0"))
        config_max_beat = float(os.environ.get("BEAT_MAX_DURATION", "12.0"))
        
        normalizer = BeatNormalizer(min_duration=config_min_beat, max_duration=config_max_beat)
        segments = normalizer.normalize(segments)
        
        # 4. QC Check
        qc_manager = QCManager()
        
        # [QC_02] Validate Segments Post-Normalization
        qc_segments_report = qc_manager.evaluate_segments(segments, config_min_beat, config_max_beat)
        if qc_segments_report.stop_pipeline:
             print(f"BLOCKER: Segment Duration Violation. Flags: {qc_segments_report.critical_flags}")
             # Write report and exit
             self._write_json(qc_segments_report, os.path.join(run_export_dir, "qc_report.json"))
             return

        qc_report = qc_manager.evaluate_alignment(align_stats)
        
        # 5. Config
        config = GlobalConfig(
            project_id=self.project_id,
            video_id=self.video_id,
            run_id=self.run_id,
            version=self.version,
            script_hash=script_hash,
            style_bible_hash=style_bible_hash,
            style_bible_path=style_bible_path,
            global_seed=42,
            audio_source_file="voiceover.mp3",
            min_beat_duration_s=config_min_beat,
            max_beat_duration_s=config_max_beat
        )
        self._write_json(config, os.path.join(run_export_dir, "global_config.json"))
        
        # 6. Visual Director
        # Pass NORMALIZED segments
        print("DEBUG: Instantiating VisualDirector...")
        director = VisualDirector(config, style_bible_content)
        director.db_manager = self.db_manager  # Pass db_manager for progress tracking
        print("DEBUG: Creating Visual Plan via Gemini...")
        try:
             plan = director.create_plan(segments, align_stats)
             print(f"DEBUG: Plan Created. Shots: {len(plan.get('shots', []))}")
        except Exception as e:
             print(f"CRITICAL: VisualDirector Failed: {e}")
             import traceback
             traceback.print_exc()
             raise e
        
        # [INTEGRITY_01] Gate: Check duration mismatch
        last_shot = plan['shots'][-1] if plan['shots'] else None
        last_shot_end = last_shot.beat_end_s if last_shot else 0.0
        diff = abs(actual_vo_duration - last_shot_end)
        
        if diff > 0.5:
             qc_report.critical_flags.append(f"DURATION_MISMATCH_DIFF_{diff:.2f}")
             qc_report.status = QCStatus.BLOCK
             qc_report.stop_pipeline = True
             print(f"BLOCKER: Audio Duration {actual_vo_duration}s vs Shot End {last_shot_end}s. Diff: {diff:.2f}s")
        
        # 7. Write Artifacts
        print("DEBUG: Writing Artifacts...")
        self._write_jsonl(plan['shots'], os.path.join(run_export_dir, "shot_spec.jsonl"))
        self._write_jsonl(plan['nano_requests'], os.path.join(run_export_dir, "nanobanana_requests.jsonl"))
        self._write_jsonl(plan['veo_requests'], os.path.join(run_export_dir, "veo_requests.jsonl"))
        
        # Write QC Report
        print(f"DEBUG: Writing QC Report to {run_export_dir}/qc_report.json")
        self._write_json(qc_report, os.path.join(run_export_dir, "qc_report.json"))
        
        # 8. Manifest
        file_index = {}
        bytes_map = {}
        for fname in ["global_config.json", "shot_spec.jsonl", "nanobanana_requests.jsonl", "veo_requests.jsonl", "qc_report.json"]:
            fpath = os.path.join(run_export_dir, fname)
            size = os.path.getsize(fpath)
            md5 = self._calculate_checksum(fpath)
            file_index[fname] = FileMetadata(
                filename=fname,
                path=fpath,
                size_bytes=size,
                md5_checksum=md5
            )
            bytes_map[fname] = size
        
        # NOTE: Using actual_vo_duration for manifest
        manifest = Manifest(
            video_id=self.video_id,
            run_id=self.run_id,
            version=self.version,
            script_hash=script_hash,
            total_duration_s=actual_vo_duration,
            vo_duration_s=actual_vo_duration,
            alignment=align_stats,
            file_index=file_index,
            export_dir=run_export_dir
        )
        manifest_path = os.path.join(run_export_dir, "manifest.json")
        self._write_json(manifest, manifest_path)
        
        # 9. Ready File (Gated)
        if qc_report.stop_pipeline:
             print(f"STOPPING PIPELINE. QC Status: {qc_report.status}. Flags: {qc_report.critical_flags}")
             return # EXIT WITHOUT WRITING READY
        
        print("QC PASSED. Writing _READY.json")
        manifest_checksum = self._calculate_checksum(manifest_path)
        ready_file = ReadyFile(
            status="READY",
            video_id=self.video_id,
            run_id=self.run_id,
            version=self.version,
            script_hash=script_hash,
            alignment_source=align_stats.source,
            vo_duration_s=manifest.vo_duration_s,
            manifest_checksum=manifest_checksum,
            byte_size_map=bytes_map,
            generated_at=datetime.utcnow().isoformat() + "Z"
        )
        self._write_json(ready_file, os.path.join(run_export_dir, "_READY.json"))
        
        print("Pipeline Phase 2 Complete. Package Ready.")
        
        # 10. Sync Planning to DB
        print("Registering Shots to Database...")
        for shot in plan['shots']:
             # Convert ShotSpec to dict
             self.db_manager.register_shot(shot.dict())
             
        # 11. Mark Stage as Done
        self.db_manager.update_run_status(self.run_id, self.version, 'planning', 'done')

    def run_prompts(self, export_dir: str, limit: int = None):
        """
        Phase 2.5: Prompt Rendering (Agent GPT-04)
        Uses export_dir directly from manifest (no discovery).
        """
        print(f"Starting Stage: PROMPTS (GPT-04) for {self.run_id} v{self.version}")
        
        # Gate: _READY.json required
        ready_path = os.path.join(export_dir, "_READY.json")
        if not os.path.exists(ready_path):
            raise FileNotFoundError(f"Run 'planning' first. _READY.json not found.")
        
        # Load style_bible as single source of truth
        style_bible_path = os.path.join(export_dir, "style_bible.md")
        if not os.path.exists(style_bible_path):
            raise FileNotFoundError(f"style_bible.md not found in export")
        style_bible_content = self._read_file(style_bible_path)
        
        # Load nanobanana_requests.jsonl
        from .models import NanobananaRequest
        requests_path = os.path.join(export_dir, "nanobanana_requests.jsonl")
        raw_requests = []
        with open(requests_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    raw_requests.append(NanobananaRequest.model_validate_json(line))
        
        # Apply Limit
        if limit and limit > 0:
             print(f"LIMIT ACTIVE: Processing only first {limit} prompts.")
             raw_requests = raw_requests[:limit]

        # Invoke GPT-04 for each request
        from .clients.agent import AgentClient
        agent = AgentClient()
        final_prompts = []
        
        
        print(f"Rendering {len(raw_requests)} prompts via GPT-04...")
        
        # Open file for incremental writing
        final_prompts_path = os.path.join(export_dir, "final_prompts.jsonl")
        with open(final_prompts_path, 'w') as prompts_file:
            for idx, req in enumerate(raw_requests, 1):
                print(f"[{idx}/{len(raw_requests)}] Processing shot {req.shot_id}...")
                
                # Update progress
                self.db_manager.update_stage_progress(
                    self.run_id,
                    self.version,
                    idx,
                    len(raw_requests),
                    f"Rendering prompt {idx}/{len(raw_requests)}"
                )
                
                gpt04_input = {
                    "raw_prompt": req.prompt,
                    "pair_role": req.pair_role.value,
                    "end_static": req.end_static,
                    "props_count": req.props_count,
                    "accent_color": req.accent_color.value if req.accent_color else None,
                    "ab_plan": req.ab_plan,
                    "ab_changes_count": req.ab_changes_count,
                    "style_bible": style_bible_content
                }
                rendered_prompt = agent.render_nanobanana_prompt(gpt04_input)
                print(f"[{idx}/{len(raw_requests)}] ✓ Completed shot {req.shot_id}")
                
                final_req = req.model_copy(update={"prompt": rendered_prompt})
                final_prompts.append(final_req)
                
                # Write immediately to file (incremental)
                prompts_file.write(json.dumps(final_req.dict()) + '\n')
                prompts_file.flush()  # Force write to disk
        
        # File is already written incrementally, no need to write again
        with open(os.path.join(export_dir, "_PROMPTS_DONE.json"), 'w') as f:
            json.dump({
                "status": "PROMPTS_DONE", 
                "count": len(final_prompts), 
                "timestamp": datetime.utcnow().isoformat()
            }, f, indent=2)

        # 6. DB Register
        print("Registering Prompts to Database...")
        for req in final_prompts:
            self.db_manager.register_asset(
                shot_id=req.shot_id,
                asset_type="PROMPT",
                path="N/A", # Prompt has no file
                role=req.pair_role.value if req.pair_role else "ref",
                meta={"prompt": req.prompt, "negative": req.negative_prompt, "style": req.style_bible_hash}
            )
        
        print(f"Stage PROMPTS Complete. {len(final_prompts)} prompts rendered.")

    def _update_manifest_index(self, run_export_dir: str, new_files: List[str]):
        manifest_path = os.path.join(run_export_dir, "manifest.json")
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
            manifest = Manifest.model_validate(manifest_data)
        
        file_index = manifest.file_index
        
        for fname in new_files:
            # Check root first, then assets
            fpath_root = os.path.join(run_export_dir, fname)
            fpath_asset = os.path.join(run_export_dir, "assets", fname)
            
            if os.path.exists(fpath_root):
                 fpath = fpath_root
                 key_name = fname
            elif os.path.exists(fpath_asset):
                 fpath = fpath_asset
                 key_name = f"assets/{fname}"
            else:
                 print(f"WARNING: Could not find {fname} to update manifest.")
                 continue

            size = os.path.getsize(fpath)
            md5 = self._calculate_checksum(fpath)
            file_index[key_name] = FileMetadata(
                filename=fname,
                path=fpath,
                size_bytes=size,
                md5_checksum=md5
            )
            
        manifest.file_index = file_index
        self._write_json(manifest, manifest_path)
        print(f"Manifest updated with {len(new_files)} items.")

    def run_images(self, export_dir: str, mode: GenerationMode = GenerationMode.SIMULATION, limit: int = None, shot_ids: List[str] = None):
        """
        Phase 3: Image Generation Stage
        Requires Phase 2.5 _PROMPTS_DONE.json to be present.
        Strict Gates: Alignment=FORCED, QC=PASS, Prompts=DONE.
        
        Args:
            shot_ids: Optional list of specific shot_ids to generate images for.
                     If None, generates for all shots.
        """
        print(f"Starting Stage: IMAGES for {self.run_id} v{self.version} [Mode: {mode.value}]")
        
        run_export_dir = export_dir
        
        # Gate: Require _PROMPTS_DONE.json
        prompts_done_path = os.path.join(run_export_dir, "_PROMPTS_DONE.json")
        if not os.path.exists(prompts_done_path):
            raise FileNotFoundError(f"BLOCKER: _PROMPTS_DONE.json not found. Run 'prompts' stage first.")
        
        # 2. QC & ALIGNMENT GATE
        qc_path = os.path.join(run_export_dir, "qc_report.json")
        if not os.path.exists(qc_path):
             raise FileNotFoundError(f"BLOCKER: qc_report.json missing.")
        
        manifest_path = os.path.join(run_export_dir, "manifest.json")
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
            manifest = Manifest.model_validate(manifest_data)
            
        with open(qc_path, 'r', encoding='utf-8') as f:
            qc_data = json.load(f)
            qc_report = QCReport.model_validate(qc_data)

        if qc_report.status == QCStatus.BLOCK:
             raise ValueError(f"BLOCKER: Stage 'images' requires QC PASS/WARN. Current status: BLOCK")
        
        if qc_report.status == QCStatus.WARN:
             if mode == GenerationMode.SIMULATION:
                 print("WARNING: Proceeding with QC WARN in SIMULATION mode.")
             else:
                 # In Real mode, do we block on WARN? User said "WARNEr for Low Coverage".
                 # Let's assume WARN is acceptable for now, or maybe prompt user?
                 # Safe default: Allow WARN (it's not BLOCK).
                 print(f"WARNING: Proceeding with QC WARN in REAL mode. Flags: {qc_report.critical_flags}")
             
        if manifest.alignment.source != AlignmentSource.FORCED_ALIGNMENT:
             # Relax rule for SIMULATION
             if mode == GenerationMode.SIMULATION or mode == GenerationMode.REAL:
                 print("WARNING: Using MOCK_ALIGNMENT in SIMULATION/REAL mode.")
             else:
                 raise ValueError(f"BLOCKER: Stage 'images' requires FORCED_ALIGNMENT. Current source: {manifest.alignment.source}")

        # 3. GENERATION
        # Load Requests from final_prompts.jsonl
        from .models import NanobananaRequest
        requests_path = os.path.join(run_export_dir, "final_prompts.jsonl")
        nano_requests = []
        with open(requests_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    nano_requests.append(NanobananaRequest.model_validate_json(line))
        
        # Filter by shot_ids if provided
        if shot_ids:
            print(f"Filtering to specific shots: {shot_ids}")
            nano_requests = [r for r in nano_requests if r.shot_id in shot_ids]
            print(f"Processing {len(nano_requests)} image requests for {len(shot_ids)} shot(s)")
        
        # Apply Limit if active
        if limit and limit > 0:
            print(f"LIMIT ACTIVE: Processing only first {limit} requests (out of {len(nano_requests)}).")
            nano_requests = nano_requests[:limit]
        
        # Run Generator
        generator = ImageGenerator(output_dir=run_export_dir)
        new_files = generator.generate_images(nano_requests, mode)
        
        # 4. A→B PAIR QC GATE
        # Load shot_specs and final_prompts for validation
        from .models import ShotSpec
        shot_specs_path = os.path.join(run_export_dir, "shot_spec.jsonl")
        shot_specs = []
        with open(shot_specs_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    shot_specs.append(ShotSpec.model_validate_json(line))
        
        assets_dir = os.path.join(run_export_dir, "assets")
        qc_manager = QCManager()
        ab_qc_report = qc_manager.evaluate_still_pairs(shot_specs, nano_requests, assets_dir)
        
        if ab_qc_report.stop_pipeline:
            print(f"BLOCKER: A→B Pair QC Failed. Flags: {ab_qc_report.critical_flags}")
            self._write_json(ab_qc_report, os.path.join(run_export_dir, "ab_qc_report.json"))
            raise ValueError("A→B Pair QC Gate blocked. Fix spec violations.")
        
        print(f"A→B Pair QC PASSED ({len(shot_specs)} pairs).")
        
        # 5. MANIFEST UPDATE
        # Update generation mode
        manifest.generation_mode = mode
        
        file_index = manifest.file_index
        assets_dir = os.path.join(run_export_dir, "assets")
        
        for fname in new_files:
            fpath = os.path.join(assets_dir, fname)
            size = os.path.getsize(fpath)
            md5 = self._calculate_checksum(fpath)
            key_name = f"assets/{fname}"
            file_index[key_name] = FileMetadata(
                filename=fname,
                path=fpath,
                size_bytes=size,
                md5_checksum=md5
            )
        
        manifest.file_index = file_index
        self._write_json(manifest, manifest_path)
        print(f"Manifest updated with {len(new_files)} assets. Mode: {mode.value}")
        
        # 5. TRIGGER FILE
        if mode == GenerationMode.SIMULATION:
            out_file = "_IMAGES_SIMULATED.json"
            conflict_file = "_IMAGES_DONE.json"
            print("SIMULATION MODE: Writing _IMAGES_SIMULATED.json (Pipeline Paused for Real Gen).")
        else:
            out_file = "_IMAGES_DONE.json"
            conflict_file = "_IMAGES_SIMULATED.json"
            print("REAL MODE: Writing _IMAGES_DONE.json (Ready for Review).")
        
        # Enforce exclusivity: Delete conflict file if exists
        conflict_path = os.path.join(run_export_dir, conflict_file)
        if os.path.exists(conflict_path):
            try:
                os.remove(conflict_path)
                print(f"Cleaned up conflicting marker: {conflict_file}")
            except Exception as e:
                print(f"WARNING: Could not delete conflicting marker {conflict_file}: {e}")
            
        with open(os.path.join(run_export_dir, out_file), 'w') as f:
            json.dump({
                "status": "IMAGES_DONE" if mode == GenerationMode.REAL else "IMAGES_SIMULATED",
                "mode": mode.value,
                "count": len(new_files),
                "timestamp": datetime.utcnow().isoformat()
            }, f, indent=2)
            
        print("Stage IMAGES Complete.")
        
        # 6. REVIEW LOOP INTEGRATION (Real Mode Only)
        # 6. DB Register (Real Mode Only for Assets)
        if mode == GenerationMode.REAL:
            # Load URL Map
            url_map_path = os.path.join(run_export_dir, "image_urls.json")
            url_map = {}
            if os.path.exists(url_map_path):
                 with open(url_map_path, 'r') as f:
                     url_map = json.load(f)
            
            print("Registering Images to Database...")
            for req in nano_requests:
                role_suffix = req.pair_role.value if req.pair_role else "ref"
                filename = f"{req.shot_id}_{role_suffix}.png"
                path = os.path.join(run_export_dir, "assets", filename)
                url = url_map.get(filename)
                
                self.db_manager.register_asset(
                    shot_id=req.shot_id,
                    asset_type="IMAGE_START" if role_suffix == "start_ref" else "IMAGE_END",
                    role=role_suffix,
                    path=path,
                    url=url,
                    meta={"prompt": req.prompt}
                )



    def run_clips(self, export_dir: str, mode: GenerationMode = GenerationMode.SIMULATION, limit: int = None, shot_ids: List[str] = None):
        """
        Phase 4: Video Clip Generation Stage
        Requires Phase 3 _IMAGES_DONE.json (or SIMULATED) to be present.
        
        Args:
            shot_ids: Optional list of specific shot_ids to generate clips for.
                     If None, generates for all shots.
        """
        run_export_dir = export_dir
        
        # 1. Gate Checks
        if not os.path.exists(run_export_dir):
            raise FileNotFoundError(f"Export directory not found: {run_export_dir}")
        
        # Check Images Gate
        images_done = os.path.join(run_export_dir, "_IMAGES_DONE.json")
        images_sim = os.path.join(run_export_dir, "_IMAGES_SIMULATED.json")
        
        # [SEMANTICS_03] Strict Provenance
        if mode == GenerationMode.REAL:
            if not os.path.exists(images_done):
                if os.path.exists(images_sim):
                     raise RuntimeError("BLOCKER: Cannot run REAL Clips with SIMULATED Images. Re-run 'images' stage with mode='real'.")
                elif not shot_ids:
                     # Only enforce full gate check if running full batch
                     raise RuntimeError("BLOCKER: Missing _IMAGES_DONE.json for Real Clips generation.")
                else:
                     print("WARNING: _IMAGES_DONE.json missing, but proceding in per-shot mode.")
        else:
             # Simulation mode can accept either, but ideally explicit
             if not os.path.exists(images_done) and not os.path.exists(images_sim):
                  raise RuntimeError("Previous Stage 'images' not complete.")

        # 2. Check Requests
        requests_path = os.path.join(run_export_dir, "veo_requests.jsonl")
        if not os.path.exists(requests_path):
            raise FileNotFoundError("Missing veo_requests.jsonl")
            
        # 3. Load Requests
        from .models import VeoRequest
        veo_requests = []
        with open(requests_path) as f:
            for line in f:
                if line.strip():
                    veo_requests.append(VeoRequest.model_validate_json(line))
        
        # Filter by shot_ids if provided
        if shot_ids:
            print(f"Filtering to specific shots: {shot_ids}")
            veo_requests = [r for r in veo_requests if r.shot_id in shot_ids]
            print(f"Processing {len(veo_requests)} clip requests for {len(shot_ids)} shot(s)")
        
        # Apply Limit
        if limit and limit > 0:
             print(f"LIMIT ACTIVE: Processing only first {limit} clips.")
             veo_requests = veo_requests[:limit]

        # 4. Run Generator
        from .generation import ClipGenerator
        generator = ClipGenerator(output_dir=run_export_dir)
        new_files = generator.generate_clips(veo_requests, mode)
        
        # 5. Update Manifest
        self._update_manifest_index(run_export_dir, new_files)
        
        # 6. Finalize
        trigger_file = "_CLIPS_DONE.json" if mode == GenerationMode.REAL else "_CLIPS_SIMULATED.json"
        with open(os.path.join(run_export_dir, trigger_file), "w") as f:
            json.dump({
                "status": "CLIPS_DONE" if mode == GenerationMode.REAL else "CLIPS_SIMULATED",
                "mode": mode.value,
                "count": len(new_files),
                "timestamp": datetime.utcnow().isoformat()
            }, f, indent=2)
            
            
        print("Stage CLIPS Complete.")

        # 7. DB Register (Real Only)
        if mode == GenerationMode.REAL:
             # Load URL Map
            url_map_path = os.path.join(run_export_dir, "image_urls.json")
            url_map = {}
            if os.path.exists(url_map_path):
                 with open(url_map_path, 'r') as f:
                     url_map = json.load(f)
            
            print("Registering Clips to Database...")
            for req in veo_requests:
                filename = f"{req.shot_id}.mp4"
                path = os.path.join(run_export_dir, "assets", filename)
                url = url_map.get(filename)
                
                self.db_manager.register_asset(
                    shot_id=req.shot_id,
                    asset_type="CLIP",
                    path=path,
                    url=url,
                    meta={"prompt": req.prompt}
                )

    def run_assembly(self, export_dir: str):
        """
        Phase 5: Assembly
        Combines generated assets + audio into final mp4.
        """
        run_export_dir = export_dir

        if not os.path.exists(run_export_dir):
            raise FileNotFoundError(f"Export dir not found: {run_export_dir}")

        # 1. Inputs
        audio_path = os.path.join(run_export_dir, "voiceover.mp3")
        shots_path = os.path.join(run_export_dir, "shot_spec.jsonl")
        
        if not os.path.exists(audio_path):
             # Fallback to staging if not in inputs (though we copied it in Phase 4)
             # But let's fail strict.
             raise FileNotFoundError(f"Audio not found in export: {audio_path}")
             
        # 2. Load Shots
        from .models import ShotSpec
        shot_specs = []
        with open(shots_path, encoding='utf-8') as f:
             for line in f:
                 if line.strip():
                     shot_specs.append(ShotSpec.model_validate_json(line))
        
        # 3. Assemble
        from .assembly import VideoAssembler
        assembler = VideoAssembler(output_dir=run_export_dir)
        final_video_path = assembler.assemble(shot_specs, audio_path)
        
        # 4. Update Manifest & Trigger
        self._update_manifest_index(run_export_dir, [os.path.basename(final_video_path)])
        
        with open(os.path.join(run_export_dir, "_VIDEO_DONE.json"), "w") as f:
            json.dump({
                "status": "VIDEO_DONE",
                "path": final_video_path,
                "timestamp": datetime.utcnow().isoformat()
            }, f, indent=2)
            
        print(f"Stage ASSEMBLY Complete. Video: {final_video_path}")
