"""
Project Codex — /sources router
DataSource registry and health/freshness metadata.
"""

from fastapi import APIRouter, Depends
from api.db import CodexDB
from api.dependencies import get_db

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", summary="All registered data sources with version and freshness")
def list_sources(db: CodexDB = Depends(get_db)):
    cypher = """
    MATCH (s:DataSource)
    RETURN s.name          AS name,
           s.version       AS version,
           s.loaded_at     AS loaded_at,
           s.record_count  AS record_count
    ORDER BY s.name
    """
    return db.run(cypher)
