import os
import logging
from typing import List
from src.foundation.manifest import State, Phase
from src.foundation.step_runner import Step, StepResult, StepContext

logger = logging.getLogger(__name__)

class PlaceholderStep(Step):
    """
    Generic placeholder step that logs execution and optionally creates a dummy artifact.
    """
    def __init__(self, name: str, phase: Phase, artifacts_to_create: List[str] = []):
        self._name = name
        self.phase = phase
        self.artifacts_to_create = artifacts_to_create

    @property
    def name(self) -> str:
        return self._name

    def run(self, context: StepContext) -> StepResult:
        logger.info(f"--- Step: {self.name} (Phase: {self.phase.value}) ---")
        logger.info(f"Executing placeholder logic for {self.name}...")
        
        created_artifacts = []
        for filename in self.artifacts_to_create:
            path = os.path.join(context.run_dir, filename)
            if not os.path.exists(path):
                logger.info(f"Creating dummy artifact: {filename}")
                with open(path, 'w') as f:
                    f.write(f'{{"step": "{self.name}", "status": "placeholder_artifact"}}\n')
            created_artifacts.append(path)
            
        logger.info(f"Step {self.name} Completed.")
        return StepResult(status=State.DONE, artifacts=created_artifacts)

# Define specific steps for T-007
class IngestStep(Step):
    @property
    def name(self) -> str:
        return "INGEST_VALIDATION"
    
    def run(self, context: StepContext) -> StepResult:
        logger.info("--- Step: INGEST_VALIDATION ---")
        # Ingest logic is mostly preflight (already done), but we log here.
        logger.info("Verifying input integrity (Placeholder/Log only)...")
        return StepResult(status=State.DONE)

from .planning import BeatSegmenterStep

class PlanningStep(Step):
    @property
    def name(self) -> str:
        return "PLANNING_PHASE"
    
    def run(self, context: StepContext) -> StepResult:
        logger.info("--- Starting Planning Phase ---")
        
        # T-103: Beat Segmentation
        segmenter = BeatSegmenterStep()
        res = segmenter.run(context)
        if res.status != State.DONE:
            return res
            
        # Future: T-104 Visual Planning (Placeholder for now)
        logger.info("[TODO] Visual Planning (T-104) placeholder...")
        
        return StepResult(status=State.DONE, artifacts=res.artifacts)

class PromptsStep(PlaceholderStep):
    def __init__(self):
        super().__init__(
            name="PROMPT_GENERATION", 
            phase=Phase.PROMPTS, 
            artifacts_to_create=["prompt_pack.jsonl"]
        )
