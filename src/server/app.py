
import os
import sqlite3
import shutil
from typing import List, Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.database_manager import DatabaseManager
from src.orchestrator import Pipeline
from src.models import GenerationMode

# Config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # root/src/server -> root
# Load environment variables
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = FastAPI(title="Video Pipeline Cockpit API")

# Allow CORS (for local dev of frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # root/src/server -> root
DB_PATH = os.path.join(BASE_DIR, "pipeline.db")
db = DatabaseManager(DB_PATH)

# Models
class AssetUpdate(BaseModel):
    is_selected: Optional[bool] = None
    qc_notes: Optional[str] = None
    # Add other updatable fields as needed

@app.get("/")
def health_check():
    return {"status": "ok", "service": "FinanceVideoPlatform API"}

@app.get("/api/runs")
def list_runs():
    """List all pipeline runs."""
    conn = db._get_connection()
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT * FROM runs ORDER BY created_at DESC")
        runs = [dict(row) for row in cursor.fetchall()]
        
        # Add status to each run
        for run in runs:
            status = db.get_run_status(run['run_id'], run['version'])
            run['status'] = status
            
        return runs
    finally:
        conn.close()

@app.post("/api/runs/create")
async def create_run(
    run_id: str = Body(...),
    video_id: str = Body(...),
    version: int = Body(1),
    voiceover: UploadFile = File(...),
    script: UploadFile = File(...),
    style_bible: UploadFile = File(...)
):
    """Creates a new run and saves staging files."""
    staging_dir = os.path.join(BASE_DIR, "runs", run_id, f"v{version}", "staging")
    os.makedirs(staging_dir, exist_ok=True)
    
    # Save files
    files = {
        "voiceover.mp3": voiceover,
        "script.txt": script,
        "style_bible.md": style_bible
    }
    
    for filename, file in files.items():
        with open(os.path.join(staging_dir, filename), "wb") as f:
            shutil.copyfileobj(file.file, f)
            
    # Register in DB
    db.register_run(run_id, version, video_id)
    db.update_run_status(run_id, version, "UPLOADED", "done")
    
    return {"status": "created", "run_id": run_id, "version": version}

def run_pipeline_stage(run_id: str, version: int, stage_name: str, video_id: str):
    """Executes a pipeline stage in the background."""
    try:
        pipeline = Pipeline(run_id=run_id, version=version, video_id=video_id)
        
        # Get export_dir
        # Note: We need to find the export dir if it's already running, 
        # or it will be created in stage 1.
        
        # For stage 1, we don't need export_dir passed.
        # For others, we might need to find it.
        
        # Finding export dir logic (similar to how orchestrator internally handles it)
        # However, Pipeline class doesn't expose it easily AFTER creation in .run()
        # For now, let's look for existing manifest if it's not stage 1.
        
        export_dir = None
        if stage_name != "planning":
             # Try to find existing export dir
             search_root = os.path.join(BASE_DIR, "exports", video_id)
             if os.path.exists(search_root):
                 for date_folder in os.listdir(search_root):
                     cand = os.path.join(search_root, date_folder, f"run_{run_id}", f"v{version}")
                     if os.path.exists(cand):
                         export_dir = cand
                         break
        
        db.update_run_status(run_id, version, stage_name.upper(), "running")
        
        if stage_name == "planning":
            pipeline.run()
        elif stage_name == "prompts":
            if not export_dir: raise ValueError("No planning results found")
            pipeline.run_prompts(export_dir)
        elif stage_name == "images":
            if not export_dir: raise ValueError("No prompts results found")
            pipeline.run_images(export_dir, mode=GenerationMode.REAL)
        elif stage_name == "clips":
            if not export_dir: raise ValueError("No images results found")
            pipeline.run_clips(export_dir, mode=GenerationMode.REAL)
        elif stage_name == "assembly":
            if not export_dir: raise ValueError("No clips results found")
            pipeline.run_assembly(export_dir)
            
        db.update_run_status(run_id, version, stage_name.upper(), "done")
    except Exception as e:
        print(f"PIPELINE ERROR ({stage_name}): {e}")
        db.update_run_status(run_id, version, stage_name.upper(), f"error: {str(e)}")

@app.post("/api/runs/{run_id}/stages/{stage}/execute")
async def execute_stage(
    run_id: str, 
    stage: str, 
    version: int = Body(1),
    video_id: str = Body("VID_001"),
    background_tasks: BackgroundTasks = None
):
    """Triggers a pipeline stage."""
    background_tasks.add_task(run_pipeline_stage, run_id, version, stage, video_id)
    return {"status": "running", "stage": stage}

@app.get("/api/runs/{run_id}/status")
def get_status(run_id: str, version: int = 1):
    """Returns the current status of a run."""
    status = db.get_run_status(run_id, version)
    if not status:
        raise HTTPException(404, "Run status not found")
    return status

@app.get("/api/runs/{run_id}/shots")
def get_run_details(run_id: str, version: int = 1):
    """
    Returns the full hierarchical tree for the UI (Shots -> Assets).
    """
    return db.get_shot_tree(run_id, version)

@app.get("/api/runs/{run_id}/shots/{shot_id}")
def get_single_shot(run_id: str, shot_id: str, version: int = 1):
    """
    Returns a single shot with its assets.
    """
    shot = db.get_single_shot(run_id, shot_id, version)
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    return shot

@app.get("/api/assets/{asset_id}/file")
def get_asset_file(asset_id: str):
    """
    Serves the physical file for an asset.
    """
    conn = db._get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT path FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        file_path = row['path']
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(file_path)
    finally:
        conn.close()

@app.patch("/api/assets/{asset_id}")
def update_asset(asset_id: str, update: AssetUpdate):
    """
    Updates asset state (e.g. selection, QC).
    """
    conn = db._get_connection()
    try:
        if update.is_selected is not None:
            # If selecting, deselect siblings first (Business Logic)
            if update.is_selected:
                # 1. Get info about this asset
                row = conn.execute("SELECT shot_id, type, role FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
                if not row:
                    raise HTTPException(404, "Asset not found")
                
                shot_id, a_type, role = row
                
                # 2. Deselect siblings
                query = "UPDATE assets SET is_selected = 0 WHERE shot_id = ? AND type = ?"
                params = [shot_id, a_type]
                
                if role:
                    query += " AND role = ?"
                    params.append(role)
                else:
                    query += " AND role IS NULL"
                
                conn.execute(query, tuple(params))
            
            # 3. Set new state
            conn.execute("UPDATE assets SET is_selected = ? WHERE asset_id = ?", (update.is_selected, asset_id))
            
        if update.qc_notes is not None:
             # TODO: Implement QC notes column if added, or store in metadata JSON
             pass
             
        conn.commit()
        return {"status": "updated", "asset_id": asset_id}
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.post("/api/runs/{run_id}/shots/{shot_id}/generate-images")
def generate_shot_images(run_id: str, shot_id: str, version: int = 1, video_id: str = "VID_001"):
    """
    Generate images for a specific shot only.
    """
    try:
        # Find export directory
        export_dir = None
        search_root = os.path.join(BASE_DIR, "exports", video_id)
        if os.path.exists(search_root):
            for date_folder in os.listdir(search_root):
                cand = os.path.join(search_root, date_folder, f"run_{run_id}", f"v{version}")
                if os.path.exists(cand):
                    export_dir = cand
                    break
        
        if not export_dir:
            raise ValueError(f"Export directory not found for {run_id} v{version}")
        
        # Create pipeline instance
        pipeline = Pipeline(run_id, version, video_id=video_id)
        
        # Run images stage with shot_id filter
        pipeline.run_images(export_dir, mode=GenerationMode.REAL, shot_ids=[shot_id])
        
        return {"status": "success", "shot_id": shot_id, "message": f"Images generated for {shot_id}"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/runs/{run_id}/shots/{shot_id}/generate-clips")
def generate_shot_clips(run_id: str, shot_id: str, version: int = 1, video_id: str = "VID_001"):
    """
    Generate video clip for a specific shot only.
    """
    try:
        # Find export directory (Reusing logic)
        export_dir = None
        search_root = os.path.join(BASE_DIR, "exports", video_id)
        if os.path.exists(search_root):
            for date_folder in os.listdir(search_root):
                cand = os.path.join(search_root, date_folder, f"run_{run_id}", f"v{version}")
                if os.path.exists(cand):
                    export_dir = cand
                    break
        
        if not export_dir:
            raise ValueError(f"Export directory not found for {run_id} v{version}")
        
        # Create pipeline instance
        pipeline = Pipeline(run_id, version, video_id=video_id)
        
        # Run clips stage with shot_id filter
        pipeline.run_clips(export_dir, mode=GenerationMode.REAL, shot_ids=[shot_id])
        
        return {"status": "success", "shot_id": shot_id, "message": f"Clip generated for {shot_id}"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    print(f"Starting API Server. DB Path: {DB_PATH}")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
