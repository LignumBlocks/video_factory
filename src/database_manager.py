
import sqlite3
import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

class DatabaseManager:
    """
    Manages the local SQLite database for the Video Pipeline.
    Stores 'Cold Data' (Artifacts) and 'Hot Data' (Decisions).
    """
    
    def __init__(self, db_path: str = "pipeline.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes the database schema if not exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. RUNS Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT,
                version INTEGER,
                video_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, version)
            )
        ''')
        
        # 2. SHOTS Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shots (
                shot_id TEXT PRIMARY KEY,
                run_id TEXT,
                version INTEGER,
                script_text TEXT,
                intent TEXT,
                metaphor TEXT,
                camera_config TEXT,
                duration_s REAL,
                beat_start_s REAL,
                beat_end_s REAL,
                alignment_source TEXT,
                alignment_confidence REAL,
                status TEXT DEFAULT 'PLANNED',
                FOREIGN KEY (run_id, version) REFERENCES runs (run_id, version)
            )
        ''')
        
        # Migration: Add new columns if missing (Idempotent)
        try:
            cursor.execute("ALTER TABLE shots ADD COLUMN metaphor TEXT")
        except sqlite3.OperationalError:
            pass # Already exists
            
        try:
            cursor.execute("ALTER TABLE shots ADD COLUMN camera_config TEXT")
        except sqlite3.OperationalError:
            pass # Already exists
        
        # 3. ASSETS Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                asset_id TEXT PRIMARY KEY,
                shot_id TEXT,
                type TEXT, -- 'PROMPT', 'IMAGE_START', 'IMAGE_END', 'CLIP'
                role TEXT, -- 'ref', 'start', 'end'
                path TEXT,
                url TEXT,
                metadata TEXT, -- JSON
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_selected BOOLEAN DEFAULT 0,
                cache_key TEXT, -- SHA256 hash of inputs
                FOREIGN KEY (shot_id) REFERENCES shots (shot_id)
            )
        ''')
        

        
        # 4. RUN_STATUS Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS run_status (
                run_id TEXT,
                version INTEGER,
                current_stage TEXT,
                stage_status TEXT, -- 'pending', 'running', 'done', 'error'
                progress_current INTEGER DEFAULT 0,
                progress_total INTEGER DEFAULT 0,
                progress_message TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, version)
            )
        ''')

        # Migrations for run_status
        try:
            cursor.execute("ALTER TABLE assets ADD COLUMN cache_key TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_cache_key ON assets(cache_key)")
        except sqlite3.OperationalError:
            pass # Already exists

        conn.commit()
        cursor.close()

    def find_asset_by_cache_key(self, cache_key: str):
        """Returns the first asset matching the cache key."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM assets WHERE cache_key = ? LIMIT 1", (cache_key,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
        try:
            cursor.execute("ALTER TABLE run_status ADD COLUMN progress_current INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        
        try:
            cursor.execute("ALTER TABLE run_status ADD COLUMN progress_total INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        
        try:
            cursor.execute("ALTER TABLE run_status ADD COLUMN progress_message TEXT")
        except sqlite3.OperationalError: pass
        
        conn.commit()
        conn.close()

    def register_run(self, run_id: str, version: int, video_id: str):
        """Registers a new pipeline run."""
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO runs (run_id, version, video_id) VALUES (?, ?, ?)",
                (run_id, version, video_id)
            )
            conn.commit()
        finally:
            conn.close()

    def register_shot(self, shot_spec: Dict):
        """Registers or updates a Shot plan."""
        conn = self._get_connection()
        try:
            # Serialize camera config if present
            camera_config = None
            if 'camera' in shot_spec:
                 camera_config = json.dumps(shot_spec['camera']) if isinstance(shot_spec['camera'], dict) else str(shot_spec['camera'])
            
            conn.execute('''
                INSERT OR REPLACE INTO shots 
                (shot_id, run_id, version, script_text, intent, metaphor, camera_config, duration_s, beat_start_s, beat_end_s, alignment_source, alignment_confidence, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                shot_spec.get('id'),
                shot_spec.get('run_id'),
                shot_spec.get('version', 1), # Default if missing
                shot_spec.get('script_text'),
                shot_spec.get('intent'),
                shot_spec.get('metaphor'),
                camera_config,
                shot_spec.get('duration_s'),
                shot_spec.get('beat_start_s'),
                shot_spec.get('beat_end_s'),
                shot_spec.get('alignment_source'),
                shot_spec.get('alignment_confidence'),
                'PLANNED'
            ))
            conn.commit()
        finally:
            conn.close()

    def register_asset(self, shot_id: str, asset_type: str, path: str, role: str = None, url: str = None, meta: Dict = None):
        """
        Registers a generated asset.
        Auto-selects the new asset as the active one for this type/shot.
        """
        conn = self._get_connection()
        asset_id = str(uuid.uuid4())
        meta_json = json.dumps(meta) if meta else "{}"
        
        try:
            # 1. Insert new asset
            conn.execute('''
                INSERT INTO assets (asset_id, shot_id, type, role, path, url, metadata, is_selected)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (asset_id, shot_id, asset_type, role, path, url, meta_json))
            
            # 2. Deselect siblings (Previous versions of same type/role for this shot)
            # Logic: If I insert a new CLIP, I want it selected. Old clips become unselected.
            if role:
                conn.execute('''
                    UPDATE assets SET is_selected = 0 
                    WHERE shot_id = ? AND type = ? AND role = ? AND asset_id != ?
                ''', (shot_id, asset_type, role, asset_id))
            else:
                conn.execute('''
                    UPDATE assets SET is_selected = 0 
                    WHERE shot_id = ? AND type = ? AND role IS NULL AND asset_id != ?
                ''', (shot_id, asset_type, asset_id))

            conn.commit()
            return asset_id
        finally:
            conn.close()

    def get_shot_tree(self, run_id: str, version: int):
        """Retrieves full tree for UI."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get Shots
        # Get Shots with video_id
        cursor.execute('''
            SELECT s.*, r.video_id 
            FROM shots s
            JOIN runs r ON s.run_id = r.run_id AND s.version = r.version
            WHERE s.run_id = ? AND s.version = ?
        ''', (run_id, version))
        shots = [dict(row) for row in cursor.fetchall()]
        
        for shot in shots:
            cursor.execute("SELECT * FROM assets WHERE shot_id = ?", (shot['shot_id'],))
            assets = [dict(row) for row in cursor.fetchall()]
            shot['assets'] = assets
            
            # Populate 'prompts' field for GUI
            prompts = {}
            for asset in assets:
                if asset['type'] == 'PROMPT':
                    try:
                        meta = json.loads(asset['metadata'])
                        text = meta.get('text', '')
                        
                        if asset['role'] == 'image_prompt':
                            prompts['image_a'] = text
                        elif asset['role'] == 'video_prompt':
                            prompts['video'] = text
                    except:
                        pass
            shot['prompts'] = prompts
            
        conn.close()
        return shots
    
    def get_single_shot(self, run_id: str, shot_id: str, version: int):
        """Retrieves a single shot with its assets."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the shot with video_id
        cursor.execute('''
            SELECT s.*, r.video_id 
            FROM shots s
            JOIN runs r ON s.run_id = r.run_id AND s.version = r.version
            WHERE s.shot_id = ? AND s.run_id = ? AND s.version = ?
        ''', (shot_id, run_id, version))
        
        shot_row = cursor.fetchone()
        if not shot_row:
            conn.close()
            return None
        
        shot = dict(shot_row)
        
        # Get assets for this shot
        cursor.execute("SELECT * FROM assets WHERE shot_id = ?", (shot_id,))
        assets = [dict(row) for row in cursor.fetchall()]
        shot['assets'] = assets
        
        # Populate 'prompts' field for GUI
        prompts = {}
        for asset in assets:
            if asset['type'] == 'PROMPT':
                try:
                    meta = json.loads(asset['metadata'])
                    text = meta.get('text', '')
                    
                    if asset['role'] == 'image_prompt':
                        prompts['image_a'] = text
                    elif asset['role'] == 'video_prompt':
                        prompts['video'] = text
                except:
                    pass
        shot['prompts'] = prompts
        
        conn.close()
        return shot

    def update_run_status(self, run_id: str, version: int, stage: str, status: str):
        """Updates the current status of a run's stage."""
        conn = self._get_connection()
        try:
            conn.execute('''
                INSERT INTO run_status (run_id, version, current_stage, stage_status, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(run_id, version) DO UPDATE SET
                    current_stage = excluded.current_stage,
                    stage_status = excluded.stage_status,
                    updated_at = excluded.updated_at
            ''', (run_id, version, stage, status))
            conn.commit()
        finally:
            conn.close()

    def get_run_status(self, run_id: str, version: int) -> Optional[Dict]:
        """Retrieves the current status of a run."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM run_status WHERE run_id = ? AND version = ?",
                (run_id, version)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_stage_progress(self, run_id: str, version: int, current: int, total: int, message: str = ""):
        """Updates the progress of the current stage."""
        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE run_status 
                SET progress_current = ?, progress_total = ?, progress_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE run_id = ? AND version = ?
            ''', (current, total, message, run_id, version))
            conn.commit()
        finally:
            conn.close()
