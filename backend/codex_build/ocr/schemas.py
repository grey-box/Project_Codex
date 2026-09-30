from datetime import datetime, timezone
from typing import List, Optional, Callable
import logging

from pydantic import BaseModel, Field

class FuzzyResult(BaseModel):
    matching_name: str
    matching_source: str
    matching_algorithm: str
    matching_uid: int
    matching_row_number: int
    distance: Optional[int] = None

class FuzzyMatching(BaseModel):
    results: List[FuzzyResult]