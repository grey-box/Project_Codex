"""
Tests for GET /audit/{term}.

IMPORTANT: there is no happy-path test here for "known term -> correct
breakdown." While writing one, direct verification turned up a bug that
makes that happy path currently impossible: audit_term() does
    canonical = resolve_to_base_term(session, term) or term
resolve_to_base_term() returns a 2-tuple (base, brand) on a match, never a
bare string. Since a non-empty tuple is truthy, `canonical` ends up holding
that tuple directly (never unpacked) whenever the term actually matches
something. That tuple then gets passed as a Cypher query parameter to
find_missing_translations()/find_missing_brands()/get_equivalent_brands(),
which fails with a Neo4j type-mismatch error (APOC's jaroWinklerDistance
expects a string, not a list) -> caught by the generic except -> a 500.

Notably, a zero-match term does NOT crash this way: resolve_to_base_term()
returns None on no match, so `canonical = None or term` falls through to
the plain string term. audit_term() only breaks on a MATCHING term -- the
opposite of what /translate's own zero-match crash looks like.

Per the "regression tests only, no fixes yet" policy applied across this
suite, the "known term" case gets its xfail(strict=True) test in
test_known_bugs.py, not here.
"""


def test_audit_zero_match_term_returns_clean_breakdown(client, seed):
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English", brand="Advil")

    response = client.get("/audit/Zzznonexistentdrug")

    assert response.status_code == 200
    body = response.json()
    assert body["term"] == "Zzznonexistentdrug"
    assert body["canonical"] == "Zzznonexistentdrug"
    # Only the one Country node that exists (from the seed above) shows up
    # as "missing" for this term -- find_missing_translations()/
    # find_missing_brands() iterate over every Country node in the graph,
    # not just ones related to the searched term.
    assert len(body["missing_translations"]) == 1
    assert body["missing_translations"][0]["country"] == "US"
    assert len(body["missing_brands"]) == 1
    assert body["missing_brands"][0]["country"] == "US"
    assert body["equivalent_brands"] == []
