"""
Project Codex — /drugs router
Drug lookup, search, names, interactions, conditions, and equivalents.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from api.db import CodexDB
from api.dependencies import get_db

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.get("", summary="List drugs with optional filters")
def list_drugs(
    source: str = Query(None, description="Filter by data source (e.g. rxnorm, drugbank)"),
    is_poc: bool = Query(None, description="Filter by proof-of-concept flag"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: CodexDB = Depends(get_db),
):
    filters = []
    params: dict = {"limit": limit, "offset": offset}

    if source is not None:
        filters.append("d.source = $source")
        params["source"] = source
    if is_poc is not None:
        filters.append("d.is_poc = $is_poc")
        params["is_poc"] = is_poc

    where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

    cypher = f"""
    MATCH (d:Drug)
    {where_clause}
    RETURN d.canonical_name AS canonical_name,
           d.source         AS source,
           d.source_id      AS source_id,
           d.is_poc         AS is_poc
    ORDER BY d.canonical_name
    SKIP $offset
    LIMIT $limit
    """
    return db.run(cypher, params)


@router.get("/search", summary="Search drugs by name (case-insensitive, all sources)")
def search_drugs(
    q: str = Query(..., description="Search term"),
    limit: int = Query(50, ge=1, le=500),
    db: CodexDB = Depends(get_db),
):
    cypher = """
    MATCH (d:Drug)-[:HAS_NAME]->(n:DrugName)
    WHERE toLower(n.name) CONTAINS toLower($q)
    RETURN DISTINCT d.canonical_name AS canonical_name,
                    d.source         AS source,
                    d.source_id      AS source_id,
                    d.is_poc         AS is_poc
    LIMIT $limit
    """
    return db.run(cypher, {"q": q, "limit": limit})


@router.get("/{source}/{source_id}", summary="Get drug by source and source ID")
def get_drug(source: str, source_id: str, db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (d:Drug {source: $source, source_id: $source_id})
    RETURN d.canonical_name AS canonical_name,
           d.source         AS source,
           d.source_id      AS source_id,
           d.is_poc         AS is_poc
    """
    rows = db.run(cypher, {"source": source, "source_id": source_id})
    if not rows:
        raise HTTPException(status_code=404, detail=f"Drug not found: {source}/{source_id}")
    return rows[0]


@router.get("/{source}/{source_id}/names", summary="All regional names / translations for a drug")
def get_drug_names(source: str, source_id: str, db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (d:Drug {source: $source, source_id: $source_id})-[:HAS_NAME]->(n:DrugName)
    RETURN n.name       AS name,
           n.country    AS country,
           n.language   AS language,
           n.name_type  AS name_type,
           n.is_primary AS is_primary
    """
    rows = db.run(cypher, {"source": source, "source_id": source_id})
    if not rows:
        raise HTTPException(status_code=404, detail=f"Drug not found or has no names: {source}/{source_id}")
    return rows


@router.get("/{source}/{source_id}/interactions", summary="Drug interactions for a drug")
def get_drug_interactions(source: str, source_id: str, db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (d:Drug {source: $source, source_id: $source_id})-[i:INTERACTS_WITH]->(d2:Drug)
    RETURN d2.canonical_name AS canonical_name,
           d2.source_id      AS source_id,
           i.severity        AS severity,
           i.description     AS description
    """
    return db.run(cypher, {"source": source, "source_id": source_id})


@router.get("/{source}/{source_id}/conditions", summary="Conditions treated by this drug")
def get_drug_conditions(source: str, source_id: str, db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (d:Drug {source: $source, source_id: $source_id})-[t:TREATS]->(c:Condition)
    RETURN c.canonical_name AS canonical_name,
           c.source         AS source,
           c.source_id      AS source_id,
           t.evidence_level AS evidence_level
    """
    return db.run(cypher, {"source": source, "source_id": source_id})


@router.get("/{source}/{source_id}/equivalents", summary="Same drug across other data sources")
def get_drug_equivalents(source: str, source_id: str, db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (d:Drug {source: $source, source_id: $source_id})-[:SAME_AS]-(eq:Drug)
    RETURN eq.canonical_name AS canonical_name,
           eq.source         AS source,
           eq.source_id      AS source_id,
           eq.is_poc         AS is_poc
    """
    return db.run(cypher, {"source": source, "source_id": source_id})
