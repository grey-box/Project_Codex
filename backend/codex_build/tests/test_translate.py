"""
Happy-path tests for POST /translate.

Like test_search.py, each test seeds exactly the data it needs via the
`seed` fixture rather than relying on demo language packs.
"""


def test_translate_direct_language_match(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofeno", country="MX",
         lang_code="es", lang_name="Spanish", brand="Advil")

    response = client.post("/translate", json={
        "term": "Ibuprofen", "lang": "es", "country": "MX",
    })

    assert response.status_code == 200
    body = response.json()
    # canonical is translate()'s own lowercased working variable, not the
    # Term node's stored casing ("Ibuprofen") — verified directly, not assumed.
    assert body["canonical"] == "ibuprofen"
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["translation"] == "ibuprofeno"
    assert result["language"] == "Spanish"
    assert result["brand"] == "Advil"
    assert result["country"] == "MX"


def test_translate_resolves_brand_name_input_to_canonical_first(client, seed):
    # Same data as above, but the request searches by brand name ("Advil")
    # instead of the canonical name — exercising the resolve-to-canonical
    # step the docstring promises happens before translation.
    seed(canonical="Ibuprofen", translation="ibuprofeno", country="MX",
         lang_code="es", lang_name="Spanish", brand="Advil")

    response = client.post("/translate", json={
        "term": "Advil", "lang": "es", "country": "MX",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["canonical"] == "ibuprofen"
    assert len(body["results"]) == 1
    assert body["results"][0]["translation"] == "ibuprofeno"


# ── Corner cases ─────────────────────────────────────────────────────────────
# "Requested language loaded, but no data for this specific term" (the
# fallback chain should engage) is deliberately NOT covered here. It's the
# exact mechanism of the confirmed /translate fallback-filtering bug (see the
# dedicated bug report) — asserting it now would mean asserting broken
# behavior as correct. It becomes a test once/if that bug is fixed, same
# policy as the other known bugs in test_known_bugs.py.

def test_translate_language_not_loaded_at_all_returns_empty_results(client, seed):
    # Only English is seeded; "es" has no Language node anywhere in the
    # graph. translate()'s own dict computes missing_language_pack=True for
    # this case, but TranslateResponse doesn't expose that field at all
    # (same response-model gap noted in the bug report) — so from the API
    # consumer's side, this is indistinguishable from "no translation
    # exists," which is what we can actually assert here.
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")

    response = client.post("/translate", json={
        "term": "Ibuprofen", "lang": "es", "country": "US",
    })

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_translate_country_not_seeded_for_term_returns_empty_results(client, seed):
    # The API doesn't validate that the requested country actually has data
    # for this term/language — it just filters, finds nothing, and returns
    # an empty list rather than a 400. Documenting that as current behavior,
    # not asserting it's correct.
    seed(canonical="Ibuprofen", translation="ibuprofeno", country="MX",
         lang_code="es", lang_name="Spanish", brand="Advil")

    response = client.post("/translate", json={
        "term": "Ibuprofen", "lang": "es", "country": "FR",
    })

    assert response.status_code == 200
    assert response.json()["results"] == []
