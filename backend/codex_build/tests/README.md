# API-Level Tests: Search / Translate / Languages / Packs / Audit

API-level integration tests for the drug-name translation system
(`/search`, `/translate`, `/languages`, `/packs/load`, `/audit/{term}`).
Every test hits the real FastAPI app and a real, disposable Neo4j
instance — nothing is mocked.

## Running the tests

No dev stack (`docker-compose.yml`) required — this is fully self-contained.

```bash
docker compose -f docker-compose.test.yml run --rm test-runner pytest -v
```

First run builds the test-runner image (~155s, installing dependencies
from scratch). Every run after that, as long as
`tests/requirements-test.txt` hasn't changed, reuses the cached image
and starts in a couple of seconds.

Run a single file or test the normal pytest way:
```bash
docker compose -f docker-compose.test.yml run --rm test-runner pytest tests/test_search.py -v
docker compose -f docker-compose.test.yml run --rm test-runner pytest tests/test_search.py::test_search_is_case_insensitive -v
```

Run with coverage:
```bash
docker compose -f docker-compose.test.yml run --rm test-runner pytest --cov=api --cov=codex --cov-report=term-missing
```

## What's here

| File | Covers |
| --- | --- |
| `conftest.py` | Shared fixtures — `driver`, `client`, `clean_db` (autouse, wipes the graph before every test), `seed` (factory for writing test data directly) |
| `test_smoke.py` | One test proving the whole chain works end to end |
| `test_search.py` | `POST /search` — happy paths + corner cases |
| `test_translate.py` | `POST /translate` — happy paths + corner cases |
| `test_languages.py` | `GET /languages` — happy paths + corner cases |
| `test_packs_load.py` | `POST /packs/load` — happy paths + corner cases |
| `test_audit.py` | `GET /audit/{term}` |
| `test_fuzzy_matching.py` | The `apoc.text.jaroWinklerDistance()` matching threshold specifically |
| `test_known_bugs.py` | `xfail(strict=True)` regression tests for confirmed, unfixed bugs |

## Adding a new test

Seed exactly the data your test needs, then call the endpoint through
`client`:

```python
def test_something(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")

    response = client.post("/search", params={"term": "Ibuprofen"})

    assert response.status_code == 200
```

Don't rely on the demo language packs for test data — `clean_db` wipes
them before every test runs specifically so tests never depend on
what's in `demo_language_packs/` at any given time. Seed what the test
actually needs, every time.

## Known bugs

Four confirmed, reproducible bugs exist in the code under test, none
fixed yet. Each has a regression test in `test_known_bugs.py` using
`pytest.mark.xfail(strict=True)` — the suite will flag the exact moment
any of them get fixed, since an unexpected pass is reported as a
failure under `strict=True`. See that file's docstring and the
`reason=` on each test for what's actually broken and where.
