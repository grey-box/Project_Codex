"""
Project Codex — /translate router
Core Codex use case: cross-country drug name translation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from api.db import CodexDB
from api.dependencies import get_db

router = APIRouter(prefix="/translate", tags=["translate"])


@router.get("", summary="Translate a drug name from one country to another")
def translate_name(
    name: str = Query(..., description="Source drug name (e.g. Tylenol)"),
    from_country: str = Query(..., description="ISO country code of the source name (e.g. US)"),
    to_country: str = Query(..., description="ISO country code to translate into (e.g. IN)"),
    db: CodexDB = Depends(get_db),
):
    cypher = """
    MATCH (d:Drug)-[:HAS_NAME]->(from_name:DrugName {name: $name, country: $from_country})
    MATCH (d)-[:HAS_NAME]->(to_name:DrugName {country: $to_country})
    RETURN d.canonical_name AS canonical_name,
           to_name.name     AS translated_name,
           to_name.language AS language,
           to_name.name_type AS name_type
    LIMIT 1
    """
    rows = db.run(cypher, {"name": name, "from_country": from_country, "to_country": to_country})
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No translation found for '{name}' from {from_country} to {to_country}.",
        )
    return rows[0]


@router.get("/all", summary="Get all translations for a drug name from a given country")
def translate_all(
    name: str = Query(..., description="Source drug name (e.g. Tylenol)"),
    from_country: str = Query(..., description="ISO country code of the source name (e.g. US)"),
    db: CodexDB = Depends(get_db),
):
    cypher = """
    MATCH (d:Drug)-[:HAS_NAME]->(src:DrugName {name: $name, country: $from_country})
    MATCH (d)-[:HAS_NAME]->(n:DrugName)
    WHERE n.country <> $from_country
    RETURN n.name     AS name,
           n.country  AS country,
           n.language AS language,
           n.name_type AS name_type
    """
    rows = db.run(cypher, {"name": name, "from_country": from_country})
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No translations found for '{name}' from country '{from_country}'.",
        )
    return rows
