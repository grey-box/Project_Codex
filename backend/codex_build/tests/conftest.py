"""
Shared pytest fixtures for the API-level test suite.

Run from inside the codex-api container, where the backend's dependencies
are already installed:

    docker exec codex-api pytest
"""
import sys
from pathlib import Path

# api.py, codex/, neo4j_sources/ etc. live one level up from this file.
# Inserted explicitly so `from api import app` resolves regardless of the
# working directory pytest is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

# Point every driver this codebase builds at the disposable test Neo4j
# (docker-compose.test.yml), not the dev instance — and do it before
# anything below imports codex.neo4j_driver. That module builds its driver
# ONCE, at import time, from these exact env vars:
#
#     driver = GraphDatabase.driver(os.getenv("NEO4J_URI"), ...)
#
# codex.services.translation_service and api.py both import that same
# module-level `driver` object, so there's no "pass the test URI in later"
# option — if this block runs after any of those modules get imported, the
# app is already wired to dev Neo4j and tests would corrupt real data.
# docker-compose.yml also sets NEO4J_URI as a real container env var
# (bolt://neo4j:7687), so a plain assignment here is required to override
# it — api.py's own load_dotenv() call won't clobber it either way, since
# load_dotenv() never overrides variables that are already set.
os.environ["NEO4J_URI"] = "bolt://neo4j-test:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "changeme"

import pytest
from neo4j import GraphDatabase
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def driver():
    """A driver pointed at the test Neo4j, independent of the app's own
    driver — used directly by tests/fixtures that need to seed or inspect
    data without going through the API."""
    d = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    yield d
    d.close()


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient wrapping the real app.

    Imported lazily (inside the fixture, not at module top) so the env vars
    above are guaranteed to be set before `api.py` — and everything it
    imports — gets loaded for the first time.

    Session-scoped and used as a context manager so the app's startup
    lifespan runs exactly once: api.py auto-loads every file in
    codex/language_packs/ on startup, which would be wasted work (and
    wasted time) if it reran before every single test.
    """
    from api import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db(driver, client):
    """Wipe the test graph before every test.

    Depends on `client` (not just `driver`) specifically so this always
    runs AFTER the one-time startup lifespan's language-pack auto-load —
    otherwise that seed data would still be sitting there for the first
    test that happens to run. Every test should start from a genuinely
    empty graph and seed exactly the fixture data it needs itself; relying
    on whatever the demo packs happen to contain makes tests fragile to
    unrelated changes in those files.

    Also matters because create_translation() uses MERGE, which is
    idempotent by design — leftover data from a previous test can silently
    make a later one pass or fail for the wrong reason if this doesn't run
    before every single test.
    """
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield
