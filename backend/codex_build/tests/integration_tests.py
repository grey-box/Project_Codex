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
from api import app, create_access_token
from codex.neo4j_driver import driver, create_user, get_user_by_email, delete_user

TEST_ADMIN_EMAIL = "admin@email.com"
TEST_ADMIN_PASS  = "AdminTestPassword123!"

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

# Ensures a test admin user exists in Neo4j during the test run
@pytest.fixture(scope="session", autouse=True)
def setup_test_admin():
    with driver.session() as session:
        # Check if test admin already exists; create if missing
        admin = get_user_by_email(session, TEST_ADMIN_EMAIL)
        if not admin:
            create_user(
                session,
                real_name="Test Admin",
                password=TEST_ADMIN_PASS,
                role="administrator",
                affiliation="Testing Dept",
                email=TEST_ADMIN_EMAIL
            )
    
    yield  # Let tests run
    
    # Teardown: Delete test admin after tests complete
    with driver.session() as session:
        delete_user(session, TEST_ADMIN_EMAIL)

# Generates valid JWT Auth Headers for the admin user    
@pytest.fixture
def admin_headers():
    token = create_access_token({"sub": TEST_ADMIN_EMAIL, "role": "administrator"})
    return {"Authorization": f"Bearer {token}"}

# Generates valid JWT Auth Headers for a non-admin user
@pytest.fixture
def user_headers():
    token = create_access_token({"sub": "med_user@email.com", "role": "medical professional"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def run_before_each_test(client, test_driver, admin_headers):
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
        client.post("/users", json=user, headers=admin_headers)


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


def test_get_user(client, test_driver, admin_headers):
    response = client.get(f"/users/jane@email.com", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["real_name"] == "Jane Doe"