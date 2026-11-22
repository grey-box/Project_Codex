import os
import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j import GraphDatabase
from unittest.mock import MagicMock

from pathlib import Path
import sys

# Make OCR dependencies optional
for mod in ("paddleocr", "paddle", "cv2", "scipy"):
    sys.modules.setdefault(mod, MagicMock())

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

@pytest.fixture(scope="session")
def auth_headers():
    """Log in using the default administrator credentials from .env."""
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@grey-box.ca")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "ChangeMe123!")

    with TestClient(app) as c:
        login_res = c.post(
            "/auth",
            json={"email": admin_email, "password": admin_password},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def client(test_driver, auth_headers):
    with TestClient(app) as client:
        client.headers.update(auth_headers)
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