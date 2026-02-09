from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any

class QAStatus(Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"

@dataclass
class QAResult:
    status: QAStatus
    reason: str
    retry_suggested: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

class QARulesEngine:
    """
    Registry and runner for QA validation rules.
    """
    def __init__(self):
        self._image_validators: List[Callable[[str], QAResult]] = []
        self._clip_validators: List[Callable[[str], QAResult]] = []

    def register_image_validator(self, validator: Callable[[str], QAResult]):
        self._image_validators.append(validator)

    def register_clip_validator(self, validator: Callable[[str], QAResult]):
        self._clip_validators.append(validator)

    def validate_image(self, image_path: str) -> QAResult:
        """
        Runs all registered image validators. 
        Returns first FAIL, or worst status encountered.
        """
        results = []
        for validator in self._image_validators:
            res = validator(image_path)
            results.append(res)
            if res.status == QAStatus.FAIL:
                return res # Fail fast
        
        # If no failures, check for warnings
        if any(r.status == QAStatus.WARNING for r in results):
             warnings = [r.reason for r in results if r.status == QAStatus.WARNING]
             return QAResult(QAStatus.WARNING, f"Warnings: {'; '.join(warnings)}")
             
        return QAResult(QAStatus.PASS, "All checks passed")

    def validate_clip(self, clip_path: str) -> QAResult:
        """
        Runs all registered clip validators.
        """
        results = []
        for validator in self._clip_validators:
            res = validator(clip_path)
            results.append(res)
            if res.status == QAStatus.FAIL:
                return res
        
        if any(r.status == QAStatus.WARNING for r in results):
             warnings = [r.reason for r in results if r.status == QAStatus.WARNING]
             return QAResult(QAStatus.WARNING, f"Warnings: {'; '.join(warnings)}")
             
        return QAResult(QAStatus.PASS, "All checks passed")
