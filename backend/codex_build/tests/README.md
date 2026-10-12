## Authentication Integration Coverage

The integration test suite now includes a test for the complete administrator authentication flow using the Neo4j test database.

The test logs in through `/api/login` using the test administrator credentials, verifies that a JWT access token is returned with the `administrator` role, and uses that token to access the protected `/users` endpoint.

This verifies that the real login, password authentication, JWT generation, and administrator-protected API access work together successfully.

Additional authentication coverage verifies that incorrect passwords and unknown users are rejected with `401`, unauthenticated requests to `/users` are rejected with `401`, and authenticated medical professionals are denied access to administrator-only user routes with `403`.


**## Running Unit Tests**
```bash
python -m pytest -v test.py
```

**## Setup for Integration Tests**
```bash
docker compose -f docker-compose-test.yml up
# Wait ~30 seconds for Neo4j, frontend, and api to be ready
```

**## Running Integration Tests**

```bash
python -m pytest -v integration_tests.py
```

**## Adding new integration tests**
In ```integration_test.py``` create a new test function:
```python
# Function name must begin with 'test' or pytest will not detect it.
 def test_function_name_here(client, test_driver):

   # Call api endpoints using
   response = client.get("/example_path")
   assert response.status_code == 200
```

 Keep in mind that you will need the proper permissions to call some API endpoints. To do this, you need to include ```admin_headers``` or ```user_headers``` like so:
```python
# Swap with user_headers if you want to test for a medical professional's access level
 def test_function_name_here(client, test_driver, admin_headers):

  # Swap here as well
   response = client.get("/example_path", headers=admin_headers)
   assert response.status_code == 200
```