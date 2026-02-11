from datetime import datetime
from typing import Dict, Optional, List
import json
import os
import shutil
from enum import Enum
from pydantic import BaseModel, Field

# --- Enums for Strict State Control ---

class Phase(str, Enum):
    INGEST = "INGEST"
    PLANNING = "PLANNING"
    PROMPTS = "PROMPTS"
    FRAMES = "FRAMES"
    CLIPS = "CLIPS"
    ASSEMBLY = "ASSEMBLY"

class State(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE" # Typically transient if we advance phase immediately
    FAILED = "FAILED"
    FAILED_PREFLIGHT = "FAILED_PREFLIGHT"

# --- Schema Definition (v1) ---

class ManifestApp(BaseModel):
    name: str = "videofactory"
    version: str = "0.1.0"
    git_commit: str = "unknown"

class ManifestPaths(BaseModel):
    run_root: str
    inputs_dir: str
    work_dir: str
    outputs_dir: str

class InputFileMeta(BaseModel):
    filename: str
    sha256: str
    bytes: int

class AudioInputMeta(InputFileMeta):
    duration_s: float

class BibleInputMeta(InputFileMeta):
    locked: bool

class ManifestInputs(BaseModel):
    script: InputFileMeta
    voiceover: AudioInputMeta
    style_bible: BibleInputMeta

class ManifestConfigMeta(BaseModel):
    """T-101: Config metadata frozen per RUN"""
    shot_menu_sha256: str
    system_rules_sha256: str
    menu_id: str
    schema_version: str = "1.0"

class ManifestStep(BaseModel):
    name: str = "unknown" # Added for T-007 (Step Runner)
    phase: Phase
    status: State
    timestamp: str
    metadata: Dict = {}
    error: Optional[str] = None

class RunManifest(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    created_at: str
    status: State
    app: ManifestApp
    paths: ManifestPaths
    inputs: ManifestInputs
    config: Optional[ManifestConfigMeta] = None  # T-101: frozen configs
    steps: List[ManifestStep] = []

# --- IO Operations ---

def write_run_manifest(run_id: str, manifest: RunManifest, artifacts_root: str = "artifacts"):
    """
    Writes or updates the run_manifest.json atomically (write tmp + rename).
    """
    run_dir = os.path.join(artifacts_root, run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    path = os.path.join(run_dir, "run_manifest.json")
    tmp_path = path + ".tmp"
    
    with open(tmp_path, "w", encoding='utf-8') as f:
        f.write(manifest.model_dump_json(indent=2))
        
    os.replace(tmp_path, path)

def load_run_manifest(run_id: str, artifacts_root: str = "artifacts") -> RunManifest:
    path = os.path.join(artifacts_root, run_id, "run_manifest.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Manifest not found at {path}")
    
    with open(path, "r", encoding='utf-8') as f:
        data = json.load(f)
    
    return RunManifest(**data)

def write_phase_checkpoint(run_id: str, phase_name: str, artifacts_root: str = "artifacts", metadata: Optional[Dict] = None):
    """
    Writes a _PHASE_DONE.json checkpoint.
    """
    run_dir = os.path.join(artifacts_root, run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    filename = f"_{phase_name.upper()}_DONE.json"
    checkpoint = {
        "phase": phase_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {}
    }
    
    # Atomic write for checkpoint too
    path = os.path.join(run_dir, filename)
    tmp_path = path + ".tmp"
    
    with open(tmp_path, "w", encoding='utf-8') as f:
        json.dump(checkpoint, f, indent=2)
        
    os.replace(tmp_path, path)

def validate_consistency(run_id: str, manifest: RunManifest, artifacts_root: str = "artifacts"):
    """
    Ensures that for every step in steps with status DONE:
    1. The corresponding checkpoint file exists.
    2. The checkpoint JSON contains the correct 'phase' field.
    Raises RuntimeError if inconsistent.
    """
    run_dir = os.path.join(artifacts_root, run_id)
    
    for step in manifest.steps:
        if step.status != State.DONE and step.status != State.IN_PROGRESS: 
            # Checkpoints are usually written when DONE or STARTING?
            # Orchestrator writes checkpoint at END.
            # So we only check consistency for DONE steps?
            # Actually, let's stick to completed phases logic.
            # If step.status is DONE, it means phase is complete.
            pass
        
        if step.status == State.DONE:
            phase = step.phase
            checkpoint_file = f"_{phase.value.upper()}_DONE.json"
            checkpoint_path = os.path.join(run_dir, checkpoint_file)
            
            if not os.path.exists(checkpoint_path):
                raise RuntimeError(f"CRITICAL INCONSISTENCY: Phase {phase} is marked DONE but {checkpoint_file} is missing.")
                
            try:
                with open(checkpoint_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("phase") != phase.value:
                         raise RuntimeError(f"CRITICAL INCONSISTENCY: {checkpoint_file} has invalid phase data: {data.get('phase')}")
            except json.JSONDecodeError:
                 raise RuntimeError(f"CRITICAL INCONSISTENCY: {checkpoint_file} is corrupted/invalid JSON.")

