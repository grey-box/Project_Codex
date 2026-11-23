"""
Fuzzy-matching coverage for POST /search.

search_database() runs a 6-way UNION: exact canonical, exact brand, exact
translation text, then fuzzy versions of all three via
apoc.text.jaroWinklerDistance(...) < 0.20. This file covers cases that
specifically probe that fuzzy threshold.

Related cases are covered elsewhere and NOT duplicated here:
  - Exact canonical match, exact brand match, exact translation-text
    match, and case-insensitivity all have their own tests in
    test_search.py already (happy-path + corner-case phases).
  - "Exact canonical match -> brand field handling" depends on Bug B
    (the search_database() early-return) -- that's covered by its own
    xfail regression test in test_known_bugs.py, not here.

The two threshold-boundary fixtures below ("ibuprXXXX" / "XXXprofen")
aren't realistic typos -- they're deliberately constructed so the actual
Jaro-Winkler distance sits close to the 0.20 cutoff on each side,
confirmed directly against apoc.text.jaroWinklerDistance() before writing
the test (0.1778 and 0.2222 respectively), not guessed at.
"""


def test_fuzzy_match_just_inside_threshold_matches(client, seed):
    # distance("ibuprofen", "ibuprXXXX") = 0.1778, confirmed via APOC
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")

    response = client.post("/search", params={"term": "ibuprXXXX"})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "Ibuprofen"


def test_fuzzy_match_just_outside_threshold_does_not_match(client, seed):
    # distance("ibuprofen", "XXXprofen") = 0.2222, confirmed via APOC --
    # confirms the 0.20 cutoff actually has a floor, not just that very
    # different strings fail to match.
    seed(canonical="Ibuprofen", translation="ibuprofen", country="US",
         lang_code="en", lang_name="English")

    response = client.post("/search", params={"term": "XXXprofen"})

    assert response.status_code == 200
    assert response.json() == []


def test_fuzzy_match_ambiguous_term_matches_two_different_drugs(client, seed):
    # A real-world failure mode worth guarding against: searching
    # "Nurofen" once surfaced the unrelated drug "Naproxen" as a fuzzy
    # match alongside the correct result. Reproducing the shape of that
    # with an own fixture pair, since that real data isn't available as a
    # test fixture: "loratadane" fuzzy-matches BOTH "Loratadine" (0.0400) and
    # "Loratidine" (0.0800), two distinct canonical terms, neither an
    # exact match for the query itself -- so this isn't just Bug B's
    # early-return path (that needs an EXACT canonical match to trigger).
    seed(canonical="Loratadine", translation="loratadine", country="US",
         lang_code="en", lang_name="English")
    seed(canonical="Loratidine", translation="loratidine", country="GB",
         lang_code="en", lang_name="English")

    response = client.post("/search", params={"term": "loratadane"})

    assert response.status_code == 200
    results = response.json()
    names = {r["name"] for r in results}
    # Documenting current behavior: both show up, with no ranking or
    # disambiguation between the correct-ish and wrong-ish match -- this
    # is a precision/tuning gap, not a crash.
    assert names == {"Loratadine", "Loratidine"}
