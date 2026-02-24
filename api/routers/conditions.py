"""
Project Codex — /conditions router
Condition lookup and drugs-by-condition.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from api.db import CodexDB
from api.dependencies import get_db

router = APIRouter(prefix="/conditions", tags=["conditions"])


@router.get("", summary="List conditions with optional filters")
def list_conditions(
    source: str = Query(None, description="Filter by data source (e.g. icd11, snomedct)"),
    is_poc: bool = Query(None, description="Filter by proof-of-concept flag"),
    limit: int = Query(50, ge=1, le=500),
    db: CodexDB = Depends(get_db),
):
    filters = []
    params: dict = {"limit": limit}

    if source is not None:
        filters.append("c.source = $source")
        params["source"] = source
    if is_poc is not None:
        filters.append("c.is_poc = $is_poc")
        params["is_poc"] = is_poc

    where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

    cypher = f"""
    MATCH (c:Condition)
    {where_clause}
    RETURN c.canonical_name AS canonical_name,
           c.source         AS source,
           c.source_id      AS source_id,
           c.is_poc         AS is_poc
    ORDER BY c.canonical_name
    LIMIT $limit
    """
    return db.run(cypher, params)


@router.get("/{source}/{source_id}", summary="Get condition by source and source ID")
def get_condition(source: str, source_id: str, db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (c:Condition {source: $source, source_id: $source_id})
    RETURN c.canonical_name AS canonical_name,
           c.source         AS source,
           c.source_id      AS source_id,
           c.is_poc         AS is_poc
    """
    rows = db.run(cypher, {"source": source, "source_id": source_id})
    if not rows:
        raise HTTPException(status_code=404, detail=f"Condition not found: {source}/{source_id}")
    return rows[0]


@router.get("/{source}/{source_id}/drugs", summary="Drugs that treat this condition")
def get_condition_drugs(source: str, source_id: str, db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (drug:Drug)-[t:TREATS]->(c:Condition {source: $source, source_id: $source_id})
    RETURN drug.canonical_name AS canonical_name,
           drug.source         AS source,
           drug.source_id      AS source_id,
           t.evidence_level    AS evidence_level
    """
    rows = db.run(cypher, {"source": source, "source_id": source_id})
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Condition not found or no drugs associated: {source}/{source_id}",
        )
    return rows
