"""
Project Codex — FastAPI application entry point.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from neo4j_sources.config import API_TITLE, API_DESCRIPTION, API_VERSION
from neo4j_sources.db import CodexDB
from neo4j_sources.dependencies import get_db
from neo4j_sources.routers import translate, drugs, conditions, sources

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)

# Register routers
app.include_router(translate.router)
app.include_router(drugs.router)
app.include_router(conditions.router)
app.include_router(sources.router)


@app.get("/health", tags=["health"], summary="API status and Neo4j connectivity check")
def health(db: CodexDB = Depends(get_db)):
    if db.ping():
        return {"status": "ok"}
    return {"status": "error", "detail": "Neo4j unreachable"}
