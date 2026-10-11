
## Running Unit Tests
```bash
python -m pytest -v test.py
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
