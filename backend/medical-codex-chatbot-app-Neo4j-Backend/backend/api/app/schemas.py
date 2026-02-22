"""Pydantic response schemas for the API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DatasetMetadata(BaseModel):
    key: str
    label: str
    id_property: str
    display_property: str
    code_property: Optional[str] = None
    description: str


class NodeSummary(BaseModel):
    dataset: str
    identifier: str
    display: Optional[str] = None
    code: Optional[str] = None
    dataset_tag: Optional[str] = None
    properties: Dict[str, Any]


class NodeDetail(NodeSummary):
    child_count: int
    parent_count: int


class PaginatedChildren(BaseModel):
    dataset: str
    parent_identifier: str
    total_children: int
    offset: int
    limit: int
    children: List[NodeSummary]


class PaginatedParents(BaseModel):
    dataset: str
    child_identifier: str
    total_parents: int
    offset: int
    limit: int
    parents: List[NodeSummary]


class SearchResults(BaseModel):
    dataset: str
    query: str
    offset: int
    limit: int
    results: List[NodeSummary]


class HealthResponse(BaseModel):
    ok: bool
    neo4j: bool
