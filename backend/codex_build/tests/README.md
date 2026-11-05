
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
python -m pytest -v integration_test.py
```

## Adding new integration tests
In ```integration_test.py``` create a new test function:
```python
#Function name must begin with 'test' or pytest will not detect it.
 def test_function_name_here(client, test_driver):

    #Call api endpoints using
    response = client.get("/example_path")
    assert response.status_code == 200
 ```

