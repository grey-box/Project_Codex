# ── Dependencies ──────────────────────────────────────────────────────────────
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
user     = os.getenv("NEO4J_USER",     "neo4j")
password = os.getenv("NEO4J_PASSWORD", "changeme")

driver = GraphDatabase.driver(uri, auth=(user, password))


# ── Core write ────────────────────────────────────────────────────────────────

def create_translation(session, canonical, brand, country, lang_code,
                       lang_name, translation, term_type="medication",
                       source_language="English"):
    """
    Create or update the full translation sub-graph for one drug entry.

    Nodes created / merged
    ----------------------
    Term         canonical name + metadata
    Language     ISO 639-1 code + full name
    Translation  the text of the drug name in this language, scoped to a country
    Country      ISO 3166-1 alpha-2 code
    Brand        commercial brand name  (optional)

    Relationships
    -------------
    (Translation)-[:OF_TERM]    ->(Term)
    (Translation)-[:IN_LANGUAGE]->(Language)
    (Translation)-[:USED_IN]    ->(Country)
    (Translation)-[:HAS_BRAND]  ->(Brand)
    (Brand)      -[:SOLD_IN]    ->(Country)
    """
    session.run(
        """
        MERGE (t:Term {canonical: $canonical, type: $term_type})
          ON CREATE SET t.source_language = $source_language
        MERGE (l:Language {code: $lang_code, name: $lang_name})
        MERGE (tr:Translation {text: $translation, country: $country})
        MERGE (tr)-[:OF_TERM]    ->(t)
        MERGE (tr)-[:IN_LANGUAGE]->(l)
        MERGE (c:Country {iso2: $country, name: $country})
        MERGE (tr)-[:USED_IN]   ->(c)
        """,
        canonical=canonical, country=country,
        lang_code=lang_code, lang_name=lang_name,
        translation=translation, term_type=term_type,
        source_language=source_language,
    )

    if brand is not None:
        session.run(
            """
            MATCH (t:Term {canonical: $canonical})
            MATCH (tr:Translation)-[:OF_TERM]->(t)
            WHERE tr.text = $translation AND tr.country = $country
            MATCH (c:Country {iso2: $country})
            MERGE (b:Brand {name: $brand})
            MERGE (b)-[:SOLD_IN]->(c)
            MERGE (tr)-[:HAS_BRAND]->(b)
            """,
            canonical=canonical, translation=translation,
            country=country, brand=brand,
        )

    print(f"  ↳ {canonical} / {translation} [{lang_name}, {country}]  brand={brand}")


# ── CSV import ────────────────────────────────────────────────────────────────

# Codex CSV column spec
# ┌─────────────────┬──────────────────────────────────────────────────────────┐
# │ Column          │ Notes                                                    │
# ├─────────────────┼──────────────────────────────────────────────────────────┤
# │ DrugBank ID     │ Optional  – links same drug across language files        │
# │ Generic Name    │ Required  – drug name in the source language             │
# │ Brand Name      │ Optional  – one commercial brand for this row            │
# │ Country         │ Required  – ISO 3166-1 alpha-2 e.g. "US", "MX"         │
# │ Source Language │ Required  – full name e.g. "English", "Spanish"         │
# │ Language Code   │ Required  – ISO 639-1 e.g. "en", "es"                  │
# └─────────────────┴──────────────────────────────────────────────────────────┘
#
# One row per (drug, brand, country).  Multiple brands for the same drug in
# the same country = multiple rows with the same Generic Name but different
# Brand Name values.  There is no Synonyms column — each alternate name is
# its own row.

def import_csv_drugs(session, rows: list) -> int:
    """
    Import drug records from a Codex-format CSV into Neo4j.

    For each row:
      1. Upserts a Term node (canonical name + DrugBank ID).
      2. Calls create_translation so Language / Country / Translation / Brand
         nodes are all created immediately, making GET /csv, /countries, and
         /languages return data right after upload.

    The Generic Name is used as both the canonical term identifier AND the
    translation text for that language+country — it is the drug's name in
    its own language.

    Returns the count of rows successfully processed.
    """
    count = 0
    for row in rows:
        canonical = (
            row.get("Generic Name") or row.get("Common name") or ""
        ).strip()
        if not canonical:
            continue

        lang_name   = (row.get("Source Language") or "English").strip()
        lang_code   = (row.get("Language Code")   or "en").strip().lower()
        country_iso = (row.get("Country")         or "").strip().upper() or None
        brand       = (row.get("Brand Name")      or "").strip() or None
        drugbank_id = (row.get("DrugBank ID")     or "").strip() or None

        # Upsert Term — drugbank_id is the cross-language link used by translate
        session.run(
            """
            MERGE (t:Term {canonical: $canonical})
            ON CREATE SET
                t.type            = 'medication',
                t.source_language = $lang_name,
                t.lang_code       = $lang_code,
                t.drugbank_id     = $drugbank_id
            ON MATCH SET
                t.drugbank_id = coalesce($drugbank_id, t.drugbank_id)
            """,
            canonical=canonical,
            lang_name=lang_name,
            lang_code=lang_code,
            drugbank_id=drugbank_id,
        )

        # Build the full Translation sub-graph so all read endpoints work
        if country_iso:
            create_translation(
                session,
                canonical=canonical,
                brand=brand,
                country=country_iso,
                lang_code=lang_code,
                lang_name=lang_name,
                translation=canonical,   # generic name IS the translation text
                source_language=lang_name,
            )

        count += 1

    return count


# ── Translation lookup ────────────────────────────────────────────────────────

def translate_drug(session, term: str, source_lang: str, target_lang: str,
                   country: str = None) -> list:
    """
    Find all target-language translations for a drug identified by name in
    source_lang.

    Lookup strategy
    ---------------
    1. Exact match on Translation.text in source_lang  (generic name)
    2. Brand name match (Brand.name) in source_lang
    3. Locate the matching target Term via DrugBank ID (cross-language link).
       Falls back to the same Term node if no DrugBank ID is present.
    4. If country is supplied, results are filtered to that country only.

    Returns a list of dicts sorted alphabetically by generic_name then
    brand_name, each containing:
        generic_name, brand_name, original_language, translated_language
    """
    # ── Step 1: resolve term → source Term node ───────────────────────────────
    source_row = session.run(
        """
        MATCH (tr:Translation)-[:IN_LANGUAGE]->(l:Language {code: $lang})
        MATCH (tr)-[:OF_TERM]->(t:Term)
        WHERE toLower(tr.text) = toLower($term)
        RETURN t.canonical       AS canonical,
               t.drugbank_id     AS drugbank_id,
               t.source_language AS src_lang_name
        LIMIT 1
        """,
        lang=source_lang, term=term,
    ).single()

    if not source_row:
        # Try matching by brand name instead
        source_row = session.run(
            """
            MATCH (b:Brand)<-[:HAS_BRAND]-(tr:Translation)
            MATCH (tr)-[:IN_LANGUAGE]->(l:Language {code: $lang})
            MATCH (tr)-[:OF_TERM]->(t:Term)
            WHERE toLower(b.name) = toLower($term)
            RETURN t.canonical       AS canonical,
                   t.drugbank_id     AS drugbank_id,
                   t.source_language AS src_lang_name
            LIMIT 1
            """,
            lang=source_lang, term=term,
        ).single()

    if not source_row:
        return []

    drugbank_id   = source_row["drugbank_id"]
    src_lang_name = source_row["src_lang_name"] or source_lang

    # Normalise country for query (None means no filter)
    country_upper = country.strip().upper() if country else None

    # ── Step 2: find target-language Term (via DrugBank ID) ───────────────────
    target_rows = []

    if drugbank_id:
        target_rows = list(session.run(
            """
            MATCH (tgt_t:Term {drugbank_id: $drugbank_id})
            MATCH (tgt_tr:Translation)-[:OF_TERM]->(tgt_t)
            MATCH (tgt_tr)-[:IN_LANGUAGE]->(tgt_l:Language {code: $target_lang})
            MATCH (tgt_tr)-[:USED_IN]->(c:Country)
            WHERE ($country IS NULL OR c.iso2 = $country)
            OPTIONAL MATCH (tgt_tr)-[:HAS_BRAND]->(b:Brand)
            RETURN DISTINCT
                tgt_t.canonical AS generic_name,
                b.name          AS brand_name,
                tgt_l.name      AS translated_language
            ORDER BY toLower(tgt_t.canonical) ASC,
                     toLower(coalesce(b.name, '')) ASC
            """,
            drugbank_id=drugbank_id, target_lang=target_lang,
            country=country_upper,
        ))

    if not target_rows:
        # Fallback: use source canonical (same-language or no DrugBank ID)
        target_rows = list(session.run(
            """
            MATCH (t:Term {canonical: $canonical})
            MATCH (tgt_tr:Translation)-[:OF_TERM]->(t)
            MATCH (tgt_tr)-[:IN_LANGUAGE]->(tgt_l:Language {code: $target_lang})
            MATCH (tgt_tr)-[:USED_IN]->(c:Country)
            WHERE ($country IS NULL OR c.iso2 = $country)
            OPTIONAL MATCH (tgt_tr)-[:HAS_BRAND]->(b:Brand)
            RETURN DISTINCT
                t.canonical AS generic_name,
                b.name      AS brand_name,
                tgt_l.name  AS translated_language
            ORDER BY toLower(t.canonical) ASC,
                     toLower(coalesce(b.name, '')) ASC
            """,
            canonical=source_row["canonical"], target_lang=target_lang,
            country=country_upper,
        ))

    return [
        {
            "generic_name":        r["generic_name"],
            "brand_name":          r["brand_name"],
            "original_language":   src_lang_name,
            "translated_language": r["translated_language"],
        }
        for r in target_rows
    ]


# ── Catalogue reads ───────────────────────────────────────────────────────────

def get_translation_data(session, canonical, lang=None, country=None):
    """Retrieve all translations and related info for a given term."""
    query = """
    MATCH (t:Term)
    WHERE t.canonical = $canonical
        OR apoc.text.jaroWinklerDistance(t.canonical, $canonical) < 0.20
    MATCH (tr:Translation)-[:OF_TERM]    ->(t)
    MATCH (tr)-[:IN_LANGUAGE]->(l:Language)
    MATCH (tr)-[:USED_IN]    ->(c:Country)
    WHERE ($lang    IS NULL OR l.code  = $lang)
        AND ($country IS NULL OR c.iso2 = $country)
    OPTIONAL MATCH (tr)-[:HAS_BRAND]->(b:Brand)
    RETURN DISTINCT
        tr.text   AS translation,
        l.name    AS language,
        b.name    AS brand,
        c.iso2    AS country,
        c.name    AS country_name
    ORDER BY language, country
    """
    return list(session.run(query, canonical=canonical, lang=lang, country=country))


def get_drugs_table(session) -> list:
    """
    Return every (drug × brand) row for the frontend CSV, sorted
    alphabetically by generic_name ascending.

    Fields: generic_name, brand_name, country, original_language,
            translated_language
    """
    query = """
    MATCH (t:Term)
    MATCH (tr:Translation)-[:OF_TERM]    ->(t)
    MATCH (tr)-[:IN_LANGUAGE]->(l:Language)
    MATCH (tr)-[:USED_IN]    ->(c:Country)
    OPTIONAL MATCH (tr)-[:HAS_BRAND]->(b:Brand)
    RETURN
        t.canonical                              AS generic_name,
        b.name                                   AS brand_name,
        c.iso2                                   AS country,
        coalesce(t.source_language, 'English')   AS original_language,
        l.name                                   AS translated_language
    ORDER BY toLower(t.canonical) ASC,
             c.iso2 ASC,
             toLower(coalesce(b.name, '')) ASC
    """
    return [
        {
            "generic_name":        r["generic_name"],
            "brand_name":          r["brand_name"],
            "country":             r["country"],
            "original_language":   r["original_language"],
            "translated_language": r["translated_language"],
        }
        for r in session.run(query)
    ]


def get_countries_languages(session) -> list:
    """
    Return every Country node with its associated language(s), sorted by
    ISO code ascending.
    """
    query = """
    MATCH (c:Country)
    OPTIONAL MATCH (tr:Translation)-[:USED_IN]    ->(c)
    OPTIONAL MATCH (tr)-[:IN_LANGUAGE]->(l:Language)
    RETURN
        c.iso2 AS iso_code,
        COLLECT(DISTINCT l.name) AS languages
    ORDER BY c.iso2 ASC
    """
    rows = []
    for r in session.run(query):
        langs = sorted(lg for lg in r["languages"] if lg)
        rows.append({"iso_code": r["iso_code"], "languages": langs})
    return rows


# ── Audit helpers ─────────────────────────────────────────────────────────────

def find_missing_translations(session, term):
    query = """
    MATCH (c:Country)
    OPTIONAL MATCH (t:Term)
        WHERE t.canonical = $term
            OR apoc.text.jaroWinklerDistance(t.canonical, $term) < 0.20
    OPTIONAL MATCH (tr:Translation)-[:OF_TERM]->(t)
        WHERE tr.country = c.iso2
    RETURN
        c.iso2 AS country,
        c.name AS country_name,
        COLLECT(tr.text) AS translations
    """
    missing = []
    for row in session.run(query, term=term):
        if not row["translations"] or row["translations"] == [None]:
            missing.append({
                "country":      row["country"],
                "country_name": row["country_name"],
                "reason":       "No translation found for this country",
            })
    return missing


def find_missing_brands(session, term):
    query = """
    MATCH (c:Country)
    OPTIONAL MATCH (t:Term)
        WHERE t.canonical = $term
            OR apoc.text.jaroWinklerDistance(t.canonical, $term) < 0.20
    OPTIONAL MATCH (tr:Translation)-[:OF_TERM]->(t)
        WHERE tr.country = c.iso2
    OPTIONAL MATCH (tr)-[:HAS_BRAND]->(b:Brand)
    RETURN
        c.iso2 AS country,
        c.name AS country_name,
        COLLECT(b.name) AS brands
    """
    missing = []
    for row in session.run(query, term=term):
        if not row["brands"] or row["brands"] == [None]:
            missing.append({
                "country":      row["country"],
                "country_name": row["country_name"],
                "reason":       "No brand name found",
            })
    return missing


def get_equivalent_brands(session, term):
    query = """
    MATCH (t:Term)
        WHERE t.canonical = $term
            OR apoc.text.jaroWinklerDistance(t.canonical, $term) < 0.20
    MATCH (tr:Translation)-[:OF_TERM]->(t)
    MATCH (tr)-[:HAS_BRAND]->(b:Brand)
    MATCH (b)-[:SOLD_IN]->(c:Country)
    RETURN DISTINCT
        b.name AS brand,
        c.iso2 AS country,
        c.name AS country_name
    ORDER BY country
    """
    return list(session.run(query, term=term))


def resolve_to_base_term(session, term):
    query = """
    MATCH (t:Term)
    WHERE t.canonical = $term
    RETURN t.canonical AS base
    UNION
    MATCH (t:Term)<-[:OF_TERM]-(tr:Translation)
    WHERE tr.text = $term
    RETURN t.canonical AS base
    UNION
    MATCH (t:Term)
    WHERE apoc.text.jaroWinklerDistance(toLower(t.canonical), toLower($term)) < 0.20
    RETURN t.canonical AS base
    UNION
    MATCH (t:Term)<-[:OF_TERM]-(tr:Translation)
    WHERE apoc.text.jaroWinklerDistance(toLower(tr.text), toLower($term)) < 0.20
    RETURN t.canonical AS base
    """
    result = session.run(query, term=term).single()
    return result["base"] if result else term


def language_exists(lang_code: str) -> bool:
    with driver.session() as session:
        result = session.run(
            "MATCH (l:Language {code: $code}) RETURN l LIMIT 1",
            code=lang_code,
        ).single()
        return result is not None
