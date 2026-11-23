"""
Regression tests for known, pre-existing bugs -- kept separate from the
other test files so they're easy to find.

These are tests, not fixes: each uses pytest.mark.xfail(strict=True)
rather than being skipped or left out, so the test suite itself flags
the moment any of these get fixed -- strict=True turns an unexpected
pass into a reported failure, so nobody has to remember to come back and
remove the marker by hand.

Full write-ups, repro steps, and root-cause analysis for all four bugs
live in the dedicated bug report docs:
  - https://claude.ai/artifact/Rx7rn91bXxwsTTGhGQ8j8u (/translate fallback)
  - https://claude.ai/artifact/Hn1jaar53qQ9c4PkxU6YvE (search, audit, and
    two further bugs)
See also TESTING_LOG.md, 2026-11-12 and 2026-11-23 entries.
"""
import pytest


@pytest.mark.xfail(
    reason="search_database() early-returns the instant it hits an exact "
           "canonical match, discarding any other valid UNION matches",
    strict=True,
)
def test_search_does_not_drop_other_matches_on_exact_canonical_hit(client, seed):
    # Naproxen's brand "Ibuprofin" is fuzzy-close to "Ibuprofen" (distance
    # 0.0444, well under the 0.20 threshold) -- a genuine second match the
    # UNION finds, that the early-return then throws away.
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")
    seed(canonical="Naproxen", translation="naproxen", country="GB",
         lang_code="en", lang_name="English", brand="Ibuprofin")

    response = client.post("/search", params={"term": "Ibuprofen"})

    names = {r["name"] for r in response.json()}
    assert names == {"Ibuprofen", "Naproxen"}, (
        "expected both the exact canonical match and the fuzzy brand "
        "match on the unrelated drug"
    )


@pytest.mark.xfail(
    reason="resolve_to_base_term() returns None on zero match; translate() "
           "unpacks it without a None-check, surfacing as an unhandled 500 "
           "instead of a clean response",
    strict=True,
)
def test_translate_zero_match_term_does_not_500(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")

    response = client.post("/translate", json={
        "term": "Zzznonexistentdrug", "lang": "en", "country": "US",
    })

    assert response.status_code != 500


@pytest.mark.xfail(
    reason="audit_term() assigns resolve_to_base_term()'s raw 2-tuple "
           "straight to `canonical` without unpacking on a match, causing "
           "a Neo4j type-mismatch 500 (new bug, found 2026-11-23)",
    strict=True,
)
def test_audit_known_term_returns_breakdown_not_500(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")

    response = client.get("/audit/Ibuprofen")

    assert response.status_code == 200


@pytest.mark.xfail(
    reason="api.py's translate_term() re-filters fallback results by the "
           "originally-requested language, which a fallback result can "
           "never match by definition -- silently drops 100% of "
           "fallback-path translations (found 2026-11-12)",
    strict=True,
)
def test_translate_fallback_returns_results_not_empty(client, seed):
    # Only English seeded; "de" has no direct match and no configured
    # regional fallback chain, so translate() should fall through to the
    # universal-English fallback and find this entry.
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")

    response = client.post("/translate", json={
        "term": "Ibuprofen", "lang": "de", "country": "US",
    })

    assert len(response.json()["results"]) > 0
