"""
Project Codex — FastAPI dependency injection for Neo4j.
"""

from typing import Generator
from api.db import CodexDB


def get_db() -> Generator[CodexDB, None, None]:
    """Yield a CodexDB instance; close it after the request."""
    db = CodexDB()
    try:
        yield db
    finally:
        db.close()
