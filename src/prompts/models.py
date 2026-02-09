from pydantic import BaseModel, Field
from typing import List

class SanitizerReport(BaseModel):
    blocked_terms_found: List[str]
    rewrites_applied: bool

class PromptRow(BaseModel):
    beat_id: str
    prompt_init_frame: str
    prompt_clip: str
    negative_prompt: str
    sanitizer_report: SanitizerReport

class PromptPack(BaseModel):
    run_id: str
    prompts: List[PromptRow]
