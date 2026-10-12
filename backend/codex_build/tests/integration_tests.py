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
TEST_ADMIN_PASS = "AdminTestPassword123!"


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

    yield

    # Teardown: Delete test admin after tests complete
    with driver.session() as session:
        delete_user(session, TEST_ADMIN_EMAIL)


# Generates valid JWT Auth Headers for the admin user
@pytest.fixture
def admin_headers():
    token = create_access_token({
        "sub": TEST_ADMIN_EMAIL,
        "role": "administrator"
    })

    return {"Authorization": f"Bearer {token}"}


# Generates valid JWT Auth Headers for a non-admin user
@pytest.fixture
def user_headers():
    token = create_access_token({
        "sub": "med_user@email.com",
        "role": "medical professional"
    })

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


# ___________TEST CASES______________________________________

def test_health(client, test_driver):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_user(client, test_driver, admin_headers):
    response = client.get(
        "/users/jane@email.com",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["real_name"] == "Jane Doe"


def test_admin_login_and_access_protected_route(client):
    login_response = client.post(
        "/api/login",
        json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASS,
        },
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    assert login_data["role"] == "administrator"
    assert "access_token" in login_data

    headers = {
        "Authorization": f"Bearer {login_data['access_token']}"
    }

    users_response = client.get(
        "/users",
        headers=headers,
    )

    assert users_response.status_code == 200

def test_admin_login_wrong_password(client):
    response = client.post(
        "/api/login",
        json={
            "email": TEST_ADMIN_EMAIL,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        "/api/login",
        json={
            "email": "doesnotexist@email.com",
            "password": "SomePassword123!",
        },
    )

    assert response.status_code == 401


def test_users_requires_authentication(client):
    response = client.get("/users")

    assert response.status_code == 401


def test_medical_professional_cannot_access_admin_users(client, admin_headers):
    test_email = "medicaltest@email.com"
    test_password = "MedicalTestPassword123!"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    create_response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "real_name": "Medical Test User",
            "role": "medical professional",
            "password": test_password,
            "affiliation": "Testing Dept",
        },
    )

    assert create_response.status_code == 201

    login_response = client.post(
        "/api/login",
        json={
            "email": test_email,
            "password": test_password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    medical_headers = {
        "Authorization": f"Bearer {token}"
    }

    users_response = client.get(
        "/users",
        headers=medical_headers,
    )

    assert users_response.status_code == 403

    delete_response = client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200
