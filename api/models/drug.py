"""
Project Codex — Pydantic response models for Drug-related endpoints.
"""

from typing import Optional
from pydantic import BaseModel


class DrugName(BaseModel):
    name: str
    country: Optional[str] = None
    language: Optional[str] = None
    name_type: Optional[str] = None
    is_primary: Optional[bool] = None


class Drug(BaseModel):
    canonical_name: str
    source: str
    source_id: str
    is_poc: Optional[bool] = None


class DrugDetail(Drug):
    names: list[DrugName] = []


class DrugInteraction(BaseModel):
    canonical_name: str
    source_id: str
    severity: Optional[str] = None
    description: Optional[str] = None


class TranslationResult(BaseModel):
    canonical_name: str
    translated_name: str
    language: Optional[str] = None
    name_type: Optional[str] = None
