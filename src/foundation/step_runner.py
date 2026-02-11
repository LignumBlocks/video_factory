from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from src.foundation.manifest import State

class StepResult(BaseModel):
    status: State
    artifacts: List[str] = []
    metadata: Dict = {}
    error: Optional[str] = None

class StepContext(BaseModel):
    run_id: str
    run_dir: str
    manifest_data: Dict[str, Any] = {}
    services: Dict[str, Any] = {}
    artifacts_root: str = "artifacts"

class Step(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def run(self, context: StepContext) -> StepResult:
        pass
