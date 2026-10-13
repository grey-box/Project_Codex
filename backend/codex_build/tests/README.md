## Authentication Integration Coverage

The integration test suite includes coverage for the complete administrator authentication flow using the Neo4j test database.

The tests verify login through `/api/login`, JWT generation with the `administrator` role, and access to the protected `/users` endpoint.

Additional authentication coverage verifies that incorrect passwords and unknown users are rejected with `401`, unauthenticated requests to `/users` are rejected with `401`, and authenticated medical professionals are denied access to administrator-only user routes with `403`.

## CRUD Integration Coverage

The integration test suite includes coverage for the access-list user CRUD workflow using the Neo4j test database.

Current CRUD coverage verifies that an authenticated administrator can create users, retrieve users, list users, update user information, change assigned roles, and delete users through the protected API endpoints.

The tests verify persistence by retrieving users after create, update, and role-change operations, and by confirming that deleted users can no longer be retrieved.

During role-update testing, a response validation issue was identified because the API response was missing the `affiliation` field required by the `UserResponse` model. The backend response was corrected.

Current integration test result:

```text
12 passed
```

## Setup for Integration Tests

```bash
docker compose -f docker-compose-test.yml up
# Wait ~30 seconds for Neo4j, frontend, and api to be ready
```

## Running Integration Tests

```bash
python -m pytest -v integration_tests.py
```

## Adding new integration tests

In `integration_tests.py` create a new test function:

```python
# Function name must begin with 'test' or pytest will not detect it.
def test_function_name_here(client, test_driver):
    response = client.get("/example_path")
    assert response.status_code == 200
```

Keep in mind that some API endpoints require permissions. Include `admin_headers` or `user_headers` when testing protected routes:

```python
# Swap with user_headers if you want to test a medical professional's access level
def test_function_name_here(client, test_driver, admin_headers):
    response = client.get("/example_path", headers=admin_headers)
    assert response.status_code == 200
```