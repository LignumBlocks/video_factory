"""
Planning Phase Steps (T-103, T-104)
"""
import os
import logging
import json
from src.foundation.manifest import State, Phase
from src.foundation.step_runner import Step, StepResult, StepContext
from src.agents.beat_segmenter import BeatSegmenterAgent
from src.llm.factory import build_llm_client_from_config
from src.config.loader import load_system_rules

logger = logging.getLogger(__name__)

class BeatSegmenterStep(Step):
    """
    T-103: BeatSegmenterStep
    Executes the BeatSegmenterAgent to convert script into beats.
    """
    @property
    def name(self) -> str:
        return "BEAT_SEGMENTER"

    def run(self, context: StepContext) -> StepResult:
        logger.info(f"--- Step: {self.name} ---")
        
        # 1. Load Frozen Config (System Rules)
        config_path = os.path.join(context.run_dir, "inputs/config/system_rules.yaml")
        if not os.path.exists(config_path):
             # Fallback to repo config if frozen not found (for robustness in dev)
             config_path = "config/system_rules.yaml"
             logger.warning(f"Frozen config not found, falling back to {config_path}")
        
        system_rules = load_system_rules(config_path)
        agent_config = system_rules.agent_settings.beat_segmenter  # Direct attribute, not .get()
        
        # 2. Setup LLM Client
        llm = build_llm_client_from_config(agent_config)
        
        # 3. Load Script
        # Prefer normalized script if exists
        script_path = os.path.join(context.run_dir, "work/normalized_script.txt")
        if not os.path.exists(script_path):
            # Try raw script from inputs
            script_path = os.path.join(context.run_dir, "inputs/script.txt")
            
        if not os.path.exists(script_path):
            return StepResult(status=State.FAILED, error=f"Script not found at {script_path}")
            
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read()
            
        # 4. Initialize and Run Agent
        # Inject min/max beats from system rules if available (could be added to rules)
        # For now use defaults in agent
        agent = BeatSegmenterAgent(llm=llm)
        
        try:
            beats, meta = agent.segment_script(context.run_id, script_text)
            
            # 5. Save Artifacts
            beats_dir = os.path.join(context.run_dir, "work/beats")
            os.makedirs(beats_dir, exist_ok=True)
            
            jsonl_path = os.path.join(beats_dir, "beat_sheet.jsonl")
            meta_path = os.path.join(beats_dir, "beat_sheet.meta.json")
            
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for beat in beats:
                    f.write(beat.to_jsonl_line() + "\n")
                    
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta.to_dict(), f, indent=2)
                
            logger.info(f"Beat sheet created with {len(beats)} beats.")
            return StepResult(status=State.DONE, artifacts=[jsonl_path, meta_path])
            
        except Exception as e:
            logger.error(f"BeatSegmenterAgent failed: {e}")
            return StepResult(status=State.FAILED, error=str(e))
