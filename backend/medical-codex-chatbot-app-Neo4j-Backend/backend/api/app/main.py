"""FastAPI entry point for interacting with the Neo4j medical codex graphs."""

from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_auth_token
from .config import get_settings
from .datasets import DatasetConfig, get_dataset_config, list_datasets
from .neo4j_service import Neo4jService
from .schemas import (
    DatasetMetadata,
    HealthResponse,
    NodeDetail,
    NodeSummary,
    PaginatedChildren,
    PaginatedParents,
    SearchResults,
)
from .serializers import serialize_node

settings = get_settings()
neo4j_service = Neo4jService(settings)

app = FastAPI(
    title="Medical Codex Graph API",
    description="Unified API for DrugBank, RxNorm, ICD-11, and SNOMED CT Neo4j graphs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _dataset_or_404(dataset_key: str) -> DatasetConfig:
    try:
        return get_dataset_config(dataset_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _resolve_dataset_tag(explicit: str | None) -> str | None:
    return explicit or settings.default_dataset_tag


@app.on_event("shutdown")
def shutdown_event() -> None:
    neo4j_service.close()


@app.get("/", tags=["meta"])
def root(token: str | None = Depends(require_auth_token)) -> dict:
    return {
        "service": app.title,
        "version": app.version,
        "datasets": [cfg.key for cfg in list_datasets()],
    }


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health(token: str | None = Depends(require_auth_token)) -> HealthResponse:
    ok = neo4j_service.ping()
    return HealthResponse(ok=ok, neo4j=ok)


@app.get("/datasets", response_model=List[DatasetMetadata], tags=["datasets"])
def datasets(token: str | None = Depends(require_auth_token)) -> List[DatasetMetadata]:
    return [
        DatasetMetadata(
            key=cfg.key,
            label=cfg.label,
            id_property=cfg.id_property,
            display_property=cfg.display_property,
            code_property=cfg.code_property,
            description=cfg.description,
        )
        for cfg in list_datasets()
    ]


@app.get(
    "/datasets/{dataset_key}/nodes/{identifier}",
    response_model=NodeDetail,
    tags=["nodes"],
)
def read_node(
    dataset_key: str,
    identifier: str,
    ds: str | None = Query(default=None, description="Optional dataset tag (`ds` property) filter."),
    token: str | None = Depends(require_auth_token),
) -> NodeDetail:
    dataset = _dataset_or_404(dataset_key)
    dataset_tag = _resolve_dataset_tag(ds)
    record = neo4j_service.fetch_node(dataset, identifier, dataset_tag=dataset_tag)
    if not record:
        raise HTTPException(status_code=404, detail="Node not found")
    payload = serialize_node(dataset_key, dataset, record["node"])
    return NodeDetail(
        **payload,
        child_count=record.get("child_count", 0),
        parent_count=record.get("parent_count", 0),
    )


@app.get(
    "/datasets/{dataset_key}/nodes/{identifier}/children",
    response_model=PaginatedChildren,
    tags=["nodes"],
)
def read_children(
    dataset_key: str,
    identifier: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ds: str | None = Query(default=None, description="Optional dataset tag (`ds` property) filter."),
    token: str | None = Depends(require_auth_token),
) -> PaginatedChildren:
    dataset = _dataset_or_404(dataset_key)
    dataset_tag = _resolve_dataset_tag(ds)
    record = neo4j_service.fetch_node(dataset, identifier, dataset_tag=dataset_tag)
    if not record:
        raise HTTPException(status_code=404, detail="Node not found")
    children_rows = neo4j_service.list_children(
        dataset,
        identifier,
        limit=limit,
        offset=offset,
        dataset_tag=dataset_tag,
    )
    children = [
        NodeSummary(**serialize_node(dataset_key, dataset, row["node"]))
        for row in children_rows
    ]
    parent_payload = serialize_node(dataset_key, dataset, record["node"])
    return PaginatedChildren(
        dataset=dataset_key,
        parent_identifier=parent_payload["identifier"],
        total_children=record.get("child_count", 0),
        offset=offset,
        limit=limit,
        children=children,
    )


@app.get(
    "/datasets/{dataset_key}/nodes/{identifier}/parents",
    response_model=PaginatedParents,
    tags=["nodes"],
)
def read_parents(
    dataset_key: str,
    identifier: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ds: str | None = Query(default=None, description="Optional dataset tag (`ds` property) filter."),
    token: str | None = Depends(require_auth_token),
) -> PaginatedParents:
    dataset = _dataset_or_404(dataset_key)
    dataset_tag = _resolve_dataset_tag(ds)
    record = neo4j_service.fetch_node(dataset, identifier, dataset_tag=dataset_tag)
    if not record:
        raise HTTPException(status_code=404, detail="Node not found")
    parent_rows = neo4j_service.list_parents(
        dataset,
        identifier,
        limit=limit,
        offset=offset,
        dataset_tag=dataset_tag,
    )
    parents = [
        NodeSummary(**serialize_node(dataset_key, dataset, row["node"]))
        for row in parent_rows
    ]
    child_payload = serialize_node(dataset_key, dataset, record["node"])
    return PaginatedParents(
        dataset=dataset_key,
        child_identifier=child_payload["identifier"],
        total_parents=record.get("parent_count", 0),
        offset=offset,
        limit=limit,
        parents=parents,
    )


@app.get(
    "/datasets/{dataset_key}/search",
    response_model=SearchResults,
    tags=["search"],
)
def search_nodes(
    dataset_key: str,
    q: str = Query(..., min_length=2, description="Case-insensitive substring search."),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=5000),
    ds: str | None = Query(default=None, description="Optional dataset tag (`ds` property) filter."),
    token: str | None = Depends(require_auth_token),
) -> SearchResults:
    dataset = _dataset_or_404(dataset_key)
    dataset_tag = _resolve_dataset_tag(ds)
    rows = neo4j_service.search_nodes(dataset, q, limit=limit, offset=offset, dataset_tag=dataset_tag)
    results = [
        NodeSummary(**serialize_node(dataset_key, dataset, row["node"]))
        for row in rows
    ]
    return SearchResults(
        dataset=dataset_key,
        query=q,
        offset=offset,
        limit=limit,
        results=results,
    )
