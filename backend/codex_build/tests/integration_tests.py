import os
import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j import GraphDatabase

from pathlib import Path
import sys

# Get the path of the current file's parent's parent (the parent directory)
parent_dir = str(Path(__file__).resolve().parent.parent)

# Add it to the module search path
sys.path.append(parent_dir)

# Now you can import your module normally
from api import app


@pytest.fixture(scope="session")
def test_driver():
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "changeme"),
    )

    driver.verify_connectivity()
    yield driver
    driver.close()

@pytest.fixture
def client(test_driver):

    with TestClient(app) as client:
        yield client



@pytest.fixture(autouse=True)
def run_before_each_test(client, test_driver):
    init_users = [
        {
            "email": "jane@email.com",
            "real_name": "Jane Doe",
            "role": "Admin",
            "password": "hello world",
            "affiliation": "grey-box"
        }
    ]

    for user in init_users:
        client.post("/users", json=user)


@pytest.fixture(scope="session", autouse=True)
def cleanup_database_after_tests(test_driver):
    yield

    # Cleanup after all tests have finished
    with test_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    


#___________TEST CASES______________________________________

def test_health(client, test_driver):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_user(client, test_driver):
    response = client.get(f"/users/jane@email.com")
    assert response.status_code == 200
    assert response.json()["real_name"] == "Jane Doe"