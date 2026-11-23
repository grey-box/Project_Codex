"""
Happy-path tests for POST /search.

Each test seeds exactly the data it needs via the `seed` fixture (see
conftest.py) rather than relying on the demo language packs, so these
stay correct regardless of what's in demo_language_packs/.
"""


def test_search_by_exact_canonical_name_returns_drug(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")

    response = client.post("/search", params={"term": "Ibuprofen"})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "Ibuprofen"
    assert results[0]["type"] == "drug"
    assert results[0]["country"] == "US"
    assert results[0]["language"] == "EN"


def test_search_by_exact_brand_name_returns_brand_name_drug(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")

    response = client.post("/search", params={"term": "Advil"})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "Ibuprofen"
    assert results[0]["brand"] == "Advil"
    assert results[0]["type"] == "brand name drug"
    assert results[0]["country"] == "US"


def test_search_by_translated_term_resolves_to_canonical(client, seed):
    # English entry so the canonical-match branch has a country/language to
    # report; search_database's country/language lookup only counts
    # translations whose text equals the canonical name itself (the
    # English-equivalent entry), not whichever translation was searched for.
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")
    seed(canonical="Ibuprofen", translation="ibuprofeno", country="MX",
         lang_code="es", lang_name="Spanish", brand="Advil")

    response = client.post("/search", params={"term": "ibuprofeno"})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "Ibuprofen"
    assert results[0]["country"] == "US"
    assert results[0]["language"] == "EN"


def test_search_with_no_match_returns_empty_list(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")

    response = client.post("/search", params={"term": "Zzznonexistentdrug"})

    assert response.status_code == 200
    assert response.json() == []


# ── Corner cases ─────────────────────────────────────────────────────────────
# search_database()'s early-return on an exact canonical match is
# deliberately NOT covered here — it's a known, pre-existing bug, not a
# corner case this phase is meant to catch. It gets its own
# xfail(strict=True) regression test in test_known_bugs.py instead.

def test_search_is_case_insensitive(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")

    upper = client.post("/search", params={"term": "IBUPROFEN"})
    lower = client.post("/search", params={"term": "ibuprofen"})
    mixed = client.post("/search", params={"term": "IbuProfen"})

    assert upper.status_code == lower.status_code == mixed.status_code == 200
    assert upper.json() == lower.json() == mixed.json()
    assert len(upper.json()) == 1
    assert upper.json()[0]["name"] == "Ibuprofen"


def test_search_with_empty_term_returns_empty_list(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")

    response = client.post("/search", params={"term": ""})

    assert response.status_code == 200
    assert response.json() == []


def test_search_with_whitespace_only_term_returns_empty_list(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")

    response = client.post("/search", params={"term": "   "})

    assert response.status_code == 200
    assert response.json() == []
