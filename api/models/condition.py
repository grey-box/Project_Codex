"""
Project Codex — Pydantic response models for Condition-related endpoints.
"""

from typing import Optional
from pydantic import BaseModel


class Condition(BaseModel):
    canonical_name: str
    source: str
    source_id: str
    is_poc: Optional[bool] = None


class ConditionDetail(Condition):
    pass


class ConditionDrug(BaseModel):
    canonical_name: str
    source: str
    source_id: str
    evidence_level: Optional[str] = None
