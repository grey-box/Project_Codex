"""
Project Codex — Neo4j driver wrapper for the API layer.
Mirrors scripts/db.py but imports from api.config.
"""

from neo4j import GraphDatabase
from api.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class CodexDB:
    def __init__(self):
        self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self._driver.close()

    def run(self, cypher: str, parameters: dict = None):
        with self._driver.session() as session:
            result = session.run(cypher, parameters or {})
            return result.data()

    def ping(self) -> bool:
        """Return True if Neo4j is reachable."""
        try:
            self.run("RETURN 1")
            return True
        except Exception:
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
