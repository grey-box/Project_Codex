## Authentication Integration Coverage

The integration test suite includes coverage for the complete administrator authentication flow using the Neo4j test database.

The tests verify login through `/api/login`, JWT generation with the `administrator` role, and access to the protected `/users` endpoint.

Additional authentication coverage verifies that incorrect passwords and unknown users are rejected with `401`, unauthenticated requests to `/users` are rejected with `401`, and authenticated medical professionals are denied access to administrator-only user routes with `403`.

## CRUD Integration Coverage

The integration test suite includes coverage for the access-list user CRUD workflow using the Neo4j test database.

Current CRUD coverage verifies that an authenticated administrator can create users, retrieve users, list users, update user information, change assigned roles, and delete users through the protected API endpoints.

The tests verify persistence by retrieving users after create, update, and role-change operations, and by confirming that deleted users can no longer be retrieved.

During role-update testing, a response validation issue was identified because the API response was missing the `affiliation` field required by the `UserResponse` model. The backend response was corrected.

## Running Integration Tests

```bash
docker compose -f docker-compose-test.yml up 
# this may take a few moments
```

Wait until the test-runner container is initialized, then:

```bash
docker compose -f docker-compose-test.yml exec test-runner pytest -v ../app/tests/integration_tests.py
```

This allows for tests to be changed and run the above command multiple times without restarting the docker container.

### Running grouped tests
By default the above pytest command will run all tests Within `integration_tests.py`. Tests on similar functions are grouped using pytest marks. To run with these marks, add the following option to the exec command.
```bash
    pytest -m [arg]
```

#### Currently supported args include:
- **health**: Tests only api health.
- **paths**: Test cases for loading language packs.
- **fuzzy**: Test cases for fuzzy search.
- **auth**: Test cases for user and admin authentication.

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

## Corner-Case and Safeguard Coverage

The integration test suite includes error-handling and administrator safeguard coverage for the access-list API.

Current coverage verifies that duplicate user creation returns `409`, missing required user fields return `422`, nonexistent user and role operations return `404`, and invalid authentication tokens return `401`.

Administrator safeguards prevent an administrator from deleting their own account and prevent the last administrator from being demoted through either the dedicated role endpoint or the general user update endpoint. Demotion is still allowed when another administrator remains.

Authentication also validates the user against the current Neo4j database state. Tokens belonging to deleted users are rejected with `401`, and previously issued administrator tokens use the current database role for the user so a demoted administrator immediately loses administrator access.