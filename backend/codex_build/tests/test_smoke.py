"""
One trivial test to prove the whole chain works: test runner -> test Neo4j
-> FastAPI app -> response. If this fails, the problem is in the test
infrastructure (conftest.py, docker-compose.test.yml), not in anything
real yet -- fix this before writing or trusting any other test.
"""


def test_languages_endpoint_is_reachable(client):
    response = client.get("/languages")

    assert response.status_code == 200

    body = response.json()
    assert "languages" in body
    assert isinstance(body["languages"], list)
