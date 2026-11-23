"""
Happy-path tests for POST /packs/load.

Verified directly against Neo4j via the `driver` fixture rather than
through /search or /translate, since those endpoints have their own
quirks that would otherwise get tangled up with what this file is
actually checking: did the pack get written correctly.
"""
import json


def _upload(client, pack: dict, filename: str = "pack.json"):
    return client.post(
        "/packs/load",
        files={"file": (filename, json.dumps(pack).encode(), "application/json")},
    )


def test_load_pack_single_term_with_brand(client, driver):
    pack = {
        "language": {"code": "pt", "name": "Portuguese"},
        "terms": [
            {
                "canonical": "Ibuprofen",
                "entries": [
                    {"translation": "ibuprofeno", "country": "BR", "brand": "Advil"}
                ],
            }
        ],
    }

    response = _upload(client, pack)

    assert response.status_code == 201
    assert response.json() == {"message": "Loaded language pack: Portuguese"}

    with driver.session() as session:
        record = session.run("""
            MATCH (t:Term {canonical: 'Ibuprofen'})<-[:OF_TERM]-(tr:Translation {text: 'ibuprofeno'})
            MATCH (tr)-[:IN_LANGUAGE]->(l:Language {code: 'pt'})
            OPTIONAL MATCH (tr)-[:USED_IN]->(c:Country)
            OPTIONAL MATCH (tr)-[:HAS_BRAND]->(b:Brand)
            RETURN c.iso2 AS country, b.name AS brand
        """).single()

    assert record is not None
    assert record["country"] == "BR"
    assert record["brand"] == "Advil"


def test_load_pack_entry_without_brand(client, driver):
    # "brand" is optional per the documented pack format — entries.get("brand")
    # can be None, and load_language_pack()/create_translation() should
    # handle that by simply not creating a Brand node at all.
    pack = {
        "language": {"code": "pt", "name": "Portuguese"},
        "terms": [
            {
                "canonical": "Paracetamol",
                "entries": [
                    {"translation": "paracetamol", "country": "BR"}
                ],
            }
        ],
    }

    response = _upload(client, pack)

    assert response.status_code == 201

    with driver.session() as session:
        record = session.run("""
            MATCH (t:Term {canonical: 'Paracetamol'})<-[:OF_TERM]-(tr:Translation {text: 'paracetamol'})
            OPTIONAL MATCH (tr)-[:HAS_BRAND]->(b:Brand)
            RETURN b IS NULL AS no_brand
        """).single()

    assert record is not None
    assert record["no_brand"] is True


def test_load_pack_same_term_multiple_countries(client, driver):
    # One term, two entries in the same pack — exercises the per-entry
    # loop inside load_language_pack() rather than just the per-term one.
    pack = {
        "language": {"code": "pt", "name": "Portuguese"},
        "terms": [
            {
                "canonical": "Ibuprofen",
                "entries": [
                    {"translation": "ibuprofeno", "country": "BR", "brand": "Advil"},
                    {"translation": "ibuprofeno", "country": "PT", "brand": "Brufen"},
                ],
            }
        ],
    }

    response = _upload(client, pack)

    assert response.status_code == 201

    with driver.session() as session:
        countries = session.run("""
            MATCH (t:Term {canonical: 'Ibuprofen'})<-[:OF_TERM]-(tr:Translation)
            MATCH (tr)-[:USED_IN]->(c:Country)
            RETURN collect(DISTINCT c.iso2) AS countries
        """).single()["countries"]

    assert sorted(countries) == ["BR", "PT"]


# ── Corner cases ─────────────────────────────────────────────────────────────

def test_load_pack_rejects_non_json_extension(client):
    response = client.post(
        "/packs/load",
        files={"file": ("pack.txt", b"{}", "text/plain")},
    )

    assert response.status_code == 400


def test_load_pack_malformed_json_returns_500_not_400(client):
    # api.py validates the file EXTENSION (.json → 400 above) but not the
    # file's actual contents — a malformed body still passes that check,
    # then load_language_pack()'s json.load() raises, which the generic
    # `except Exception` in load_pack() converts to a 500, not a 400.
    # Documenting this inconsistency as current behavior, not asserting
    # it's correct.
    response = client.post(
        "/packs/load",
        files={"file": ("pack.json", b"{not valid json", "application/json")},
    )

    assert response.status_code == 500


def test_load_pack_missing_required_field_returns_500(client):
    # Valid JSON, but missing the "language" key entirely — load_language_pack()
    # does pack["language"]["code"] unconditionally, so this is a KeyError,
    # caught by the same generic except and surfaced as a 500.
    pack = {"terms": [{"canonical": "Ibuprofen", "entries": []}]}

    response = _upload(client, pack)

    assert response.status_code == 500


def test_load_pack_same_pack_twice_is_idempotent(client, driver):
    # create_translation() uses MERGE throughout — loading the identical
    # pack a second time should not create duplicate nodes or relationships.
    pack = {
        "language": {"code": "pt", "name": "Portuguese"},
        "terms": [
            {
                "canonical": "Ibuprofen",
                "entries": [
                    {"translation": "ibuprofeno", "country": "BR", "brand": "Advil"}
                ],
            }
        ],
    }

    first = _upload(client, pack)
    second = _upload(client, pack)

    assert first.status_code == 201
    assert second.status_code == 201

    with driver.session() as session:
        counts = session.run("""
            MATCH (t:Term {canonical: 'Ibuprofen'}) WITH count(t) AS terms
            MATCH (tr:Translation {text: 'ibuprofeno'}) WITH terms, count(tr) AS translations
            MATCH (b:Brand {name: 'Advil'}) WITH terms, translations, count(b) AS brands
            RETURN terms, translations, brands
        """).single()

    assert counts["terms"] == 1
    assert counts["translations"] == 1
    assert counts["brands"] == 1
