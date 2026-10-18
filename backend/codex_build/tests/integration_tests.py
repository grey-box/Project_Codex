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


def test_admin_can_create_user(client, admin_headers):
    test_email = "crudcreate@email.com"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "real_name": "CRUD Create User",
            "role": "medical professional",
            "password": "CrudCreatePassword123!",
            "affiliation": "Testing Dept",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == test_email
    assert data["real_name"] == "CRUD Create User"
    assert data["role"] == "medical professional"
    assert data["affiliation"] == "Testing Dept"

    get_response = client.get(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["email"] == test_email

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )


def test_admin_can_list_users(client, admin_headers):
    response = client.get(
        "/users",
        headers=admin_headers,
    )

    assert response.status_code == 200

    users = response.json()

    assert isinstance(users, list)
    assert any(
        user["email"] == "jane@email.com"
        for user in users
    )


def test_admin_can_update_user(client, admin_headers):
    test_email = "crudupdate@email.com"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    create_response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "real_name": "CRUD Update User",
            "role": "medical professional",
            "password": "CrudUpdatePassword123!",
            "affiliation": "Testing Dept",
        },
    )

    assert create_response.status_code == 201

    update_response = client.patch(
        f"/users/{test_email}",
        headers=admin_headers,
        json={
            "real_name": "Updated CRUD User",
            "affiliation": "Updated Testing Dept",
        },
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["real_name"] == "Updated CRUD User"
    assert updated["affiliation"] == "Updated Testing Dept"

    get_response = client.get(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["real_name"] == "Updated CRUD User"
    assert get_response.json()["affiliation"] == "Updated Testing Dept"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )


def test_admin_can_change_user_role(client, admin_headers):
    test_email = "crudrole@email.com"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    create_response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "real_name": "CRUD Role User",
            "role": "medical professional",
            "password": "CrudRolePassword123!",
            "affiliation": "Testing Dept",
        },
    )

    assert create_response.status_code == 201

    role_response = client.put(
        f"/users/{test_email}/role",
        headers=admin_headers,
        json={
            "role": "administrator",
        },
    )

    assert role_response.status_code == 200
    assert role_response.json()["role"] == "administrator"

    get_response = client.get(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["role"] == "administrator"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )


def test_admin_can_delete_user(client, admin_headers):
    test_email = "cruddelete@email.com"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    create_response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "real_name": "CRUD Delete User",
            "role": "medical professional",
            "password": "CrudDeletePassword123!",
            "affiliation": "Testing Dept",
        },
    )

    assert create_response.status_code == 201

    delete_response = client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200

    get_response = client.get(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert get_response.status_code == 404


def test_create_duplicate_user_returns_409(client, admin_headers):
    response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": "jane@email.com",
            "real_name": "Duplicate Jane",
            "role": "medical professional",
            "password": "DuplicatePassword123!",
            "affiliation": "Testing Dept",
        },
    )

    assert response.status_code == 409


def test_get_nonexistent_user_returns_404(client, admin_headers):
    response = client.get(
        "/users/nonexistent@email.com",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_update_nonexistent_user_returns_404(client, admin_headers):
    response = client.patch(
        "/users/nonexistent@email.com",
        headers=admin_headers,
        json={
            "real_name": "Missing User",
        },
    )

    assert response.status_code == 404


def test_delete_nonexistent_user_returns_404(client, admin_headers):
    response = client.delete(
        "/users/nonexistent@email.com",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_get_role_for_nonexistent_user_returns_404(client, admin_headers):
    response = client.get(
        "/users/nonexistent@email.com/role",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_update_role_for_nonexistent_user_returns_404(client, admin_headers):
    response = client.put(
        "/users/nonexistent@email.com/role",
        headers=admin_headers,
        json={
            "role": "administrator",
        },
    )

    assert response.status_code == 404


def test_create_user_missing_required_field_returns_422(client, admin_headers):
    response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": "missingfield@email.com",
            "real_name": "Missing Field User",
            "role": "medical professional",
            "affiliation": "Testing Dept",
        },
    )

    assert response.status_code == 422


def test_invalid_token_returns_401(client):
    response = client.get(
        "/users",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_administrator_cannot_delete_own_account(client, admin_headers):
    response = client.delete(
        f"/users/{TEST_ADMIN_EMAIL}",
        headers=admin_headers,
    )

    assert response.status_code == 409

    get_response = client.get(
        f"/users/{TEST_ADMIN_EMAIL}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200


def test_last_administrator_cannot_be_demoted_by_role_endpoint(client, admin_headers):
    response = client.put(
        f"/users/{TEST_ADMIN_EMAIL}/role",
        headers=admin_headers,
        json={
            "role": "medical professional",
        },
    )

    assert response.status_code == 409

    get_response = client.get(
        f"/users/{TEST_ADMIN_EMAIL}/role",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["role"] == "administrator"


def test_last_administrator_cannot_be_demoted_by_patch(client, admin_headers):
    response = client.patch(
        f"/users/{TEST_ADMIN_EMAIL}",
        headers=admin_headers,
        json={
            "role": "medical professional",
        },
    )

    assert response.status_code == 409

    get_response = client.get(
        f"/users/{TEST_ADMIN_EMAIL}/role",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["role"] == "administrator"


def test_administrator_can_demote_user_when_another_administrator_exists(
    client,
    admin_headers,
):
    test_email = "secondadmin@email.com"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    create_response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "real_name": "Second Administrator",
            "role": "administrator",
            "password": "SecondAdminPassword123!",
            "affiliation": "Testing Dept",
        },
    )

    assert create_response.status_code == 201

    role_response = client.put(
        f"/users/{test_email}/role",
        headers=admin_headers,
        json={
            "role": "medical professional",
        },
    )

    assert role_response.status_code == 200
    assert role_response.json()["role"] == "medical professional"

    delete_response = client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200


def test_stale_admin_token_for_missing_user_returns_401(client):
    token = create_access_token({
        "sub": "formeradmin@email.com",
        "role": "administrator"
    })

    stale_admin_headers = {
        "Authorization": f"Bearer {token}"
    }

    response = client.get(
        "/users",
        headers=stale_admin_headers,
    )

    assert response.status_code == 401


def test_demoted_administrator_token_uses_current_database_role(client, admin_headers):
    test_email = "demotedadmin@email.com"
    test_password = "DemotedAdminPassword123!"

    client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    create_response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "real_name": "Demoted Administrator",
            "role": "administrator",
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

    old_admin_headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }

    role_response = client.put(
        f"/users/{test_email}/role",
        headers=admin_headers,
        json={
            "role": "medical professional",
        },
    )

    assert role_response.status_code == 200

    users_response = client.get(
        "/users",
        headers=old_admin_headers,
    )

    assert users_response.status_code == 403

    delete_response = client.delete(
        f"/users/{test_email}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200
