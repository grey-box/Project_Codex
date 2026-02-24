"""
Project Codex — Neo4j driver wrapper
"""

from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class CodexDB:
    def __init__(self):
        self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self._driver.close()

    def run(self, cypher: str, parameters: dict = None):
        with self._driver.session() as session:
            result = session.run(cypher, parameters or {})
            return result.data()

    def run_file(self, filepath: str):
        """Execute a .cypher file, skipping comment-only lines."""
        with open(filepath, "r") as f:
            content = f.read()

        # Split on semicolons to get individual statements
        statements = [s.strip() for s in content.split(";") if s.strip()]
        executed = 0
        for stmt in statements:
            # Skip pure comment blocks
            lines = [l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("//")]
            if not lines:
                continue
            self.run(stmt)
            executed += 1
        return executed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
