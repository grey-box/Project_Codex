"""
Happy-path tests for GET /languages.
"""


def test_languages_lists_each_language_with_its_countries(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")
    seed(canonical="Ibuprofen", translation="ibuprofeno", country="MX",
         lang_code="es", lang_name="Spanish")

    response = client.get("/languages")

    assert response.status_code == 200
    body = response.json()
    assert body["languages"] == ["en", "es"]
    assert body["countries"]["en"] == [{"code": "US", "label": "United States"}]
    assert body["countries"]["es"] == [{"code": "MX", "label": "Mexico"}]


def test_languages_unknown_country_code_falls_back_to_the_code_itself(client, seed):
    # "JP" isn't in api.py's COUNTRY_NAMES map, so the label should just be
    # the code itself rather than a human-readable name.
    seed(canonical="Ibuprofen", translation="ibupurofen", country="JP",
         lang_code="ja", lang_name="Japanese")

    response = client.get("/languages")

    assert response.status_code == 200
    assert response.json()["countries"]["ja"] == [{"code": "JP", "label": "JP"}]


def test_languages_includes_a_language_with_no_translations_yet(client, driver):
    # A Language node can exist with nothing pointing at it yet (e.g. a
    # pack was loaded for metadata before any terms were added). The
    # OPTIONAL MATCH in list_languages()'s query should still surface it,
    # just with an empty country list rather than being left out entirely.
    with driver.session() as session:
        session.run("MERGE (l:Language {code: 'fr', name: 'French'})")

    response = client.get("/languages")

    assert response.status_code == 200
    body = response.json()
    assert "fr" in body["languages"]
    assert body["countries"]["fr"] == []


# ── Corner cases ─────────────────────────────────────────────────────────────

def test_languages_called_before_any_pack_loaded_returns_empty_cleanly(client, driver):
    # Nothing seeded at all — not even a bare Language node. Confirms
    # this returns an empty list cleanly rather than a 500.
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    response = client.get("/languages")

    assert response.status_code == 200
    assert response.json() == {"languages": [], "countries": {}}
