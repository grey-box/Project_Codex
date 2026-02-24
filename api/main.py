"""
Project Codex — FastAPI application entry point.
"""

from fastapi import FastAPI, Depends
from api.config import API_TITLE, API_DESCRIPTION, API_VERSION
from api.db import CodexDB
from api.dependencies import get_db
from api.routers import translate, drugs, conditions, sources

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
