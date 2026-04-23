from neo4j import GraphDatabase
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import uuid

load_dotenv()

uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
user     = os.getenv("NEO4J_USER",     "neo4j")
password = os.getenv("NEO4J_PASSWORD", "changeme")

driver = GraphDatabase.driver(uri, auth=(user, password))

# Maps ISO 639-1 codes to full language names for API convenience.
LANG_CODE_MAP = {
    "en": "English",   "es": "Spanish",    "fr": "French",
    "de": "German",    "pt": "Portuguese", "uk": "Ukrainian",
    "ru": "Russian",   "ja": "Japanese",   "zh": "Chinese",
    "ar": "Arabic",    "ko": "Korean",     "it": "Italian",
    "nl": "Dutch",     "pl": "Polish",     "tr": "Turkish",
    "sv": "Swedish",   "da": "Danish",     "fi": "Finnish",
    "no": "Norwegian", "he": "Hebrew",     "fa": "Persian",
}

def resolve_language(lang: str) -> str:
    """Convert a lang code (en) or full name (English) to a full name for DB matching."""
    if not lang:
        return lang
    return LANG_CODE_MAP.get(lang.lower().strip(), lang.strip())


# Graph model
#
# (Term {concept_id, source_id, source_name, name, type,
#         country, language, uploaded_at})
#   -[:REFERS_TO]->
# (Concept {concept_id})
#
# One Concept → many Terms (same drug across languages / sources / countries).
# Concept ID is the internal universal identifier assigned at import time.


def import_csv_drugs(session, rows: list, uploaded_at: str = None) -> int:
    """
    Import rows from a Codex CSV into Neo4j.

    CSV columns:
        Concept ID   — internal universal ID; auto-generated UUID if blank
        Source ID    — ID from the external source (e.g. RXCUI, WHO code)
        Source Name  — name of the source (e.g. RxNorm, WHO)
        Name         — drug name
        Type         — Generic/Active Ingredient  or  Brand
        Country      — ISO 3166-1 alpha-2 (e.g. US, MX)
        Language     — full language name (e.g. English, Spanish)

    Returns the count of rows successfully imported.
    """
    ts = uploaded_at or datetime.now(timezone.utc).isoformat()
    count = 0

    for row in rows:
        # Normalise keys — strip whitespace and make case-insensitive
        # so minor header variations don't silently drop all rows
        norm = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}

        name = norm.get("name", "")
        if not name:
            continue

        concept_id  = norm.get("concept id",  "") or str(uuid.uuid4())
        source_id   = norm.get("source id",   "") or None
        source_name = norm.get("source name", "") or None
        term_type   = norm.get("type",        "") or "Generic/Active Ingredient"
        country     = norm.get("country",     "").upper() or None
        language    = norm.get("language",    "") or None

        session.run(
            """
            MERGE (c:Concept {concept_id: $concept_id})
            MERGE (t:Term {
                concept_id:  $concept_id,
                source_id:   $source_id,
                source_name: $source_name,
                name:        $name,
                type:        $type,
                country:     $country,
                language:    $language
            })
            ON CREATE SET t.uploaded_at = $uploaded_at
            MERGE (t)-[:REFERS_TO]->(c)
            """,
            concept_id=concept_id,
            source_id=source_id,
            source_name=source_name,
            name=name,
            type=term_type,
            country=country,
            language=language,
            uploaded_at=ts,
        )
        count += 1

    return count


def translate_term(session, term: str, source_lang: str,
                   target_lang: str, target_country: str = None,
                   source_name: str = None) -> list:
    """
    Find all target-language terms sharing the same Concept as the input term.

    Matches the input term by name and source language (case-insensitive).
    Optionally filters results by target country and source name.
    Returns a list of dicts sorted by name.
    """
    src_language = resolve_language(source_lang)
    tgt_language = resolve_language(target_lang)
    country_upper = target_country.strip().upper() if target_country else None

    results = session.run(
        """
        MATCH (src:Term)-[:REFERS_TO]->(c:Concept)
        WHERE toLower(src.name)     = toLower($name)
          AND toLower(src.language) = toLower($src_language)
        MATCH (tgt:Term)-[:REFERS_TO]->(c)
        WHERE toLower(tgt.language) = toLower($tgt_language)
          AND ($country     IS NULL OR tgt.country     = $country)
          AND ($source_name IS NULL OR toLower(tgt.source_name) = toLower($source_name))
        RETURN DISTINCT
            tgt.concept_id  AS concept_id,
            tgt.source_id   AS source_id,
            tgt.source_name AS source_name,
            tgt.name        AS name,
            tgt.type        AS type,
            tgt.country     AS country,
            tgt.language    AS language
        ORDER BY toLower(tgt.name) ASC
        """,
        name=term,
        src_language=src_language,
        tgt_language=tgt_language,
        country=country_upper,
        source_name=source_name,
    )

    return [dict(r) for r in results]


def get_all_terms(session) -> list:
    """Return every Term node sorted alphabetically by name."""
    results = session.run(
        """
        MATCH (t:Term)
        RETURN
            t.concept_id  AS concept_id,
            t.source_id   AS source_id,
            t.source_name AS source_name,
            t.name        AS name,
            t.type        AS type,
            t.country     AS country,
            t.language    AS language,
            t.uploaded_at AS uploaded_at
        ORDER BY toLower(t.name) ASC
        """
    )
    return [dict(r) for r in results]


def get_terms_by_concept(session, concept_id: str) -> list:
    """Return all Terms linked to a given Concept ID."""
    results = session.run(
        """
        MATCH (t:Term)-[:REFERS_TO]->(c:Concept {concept_id: $concept_id})
        RETURN
            t.concept_id  AS concept_id,
            t.source_id   AS source_id,
            t.source_name AS source_name,
            t.name        AS name,
            t.type        AS type,
            t.country     AS country,
            t.language    AS language,
            t.uploaded_at AS uploaded_at
        ORDER BY toLower(t.name) ASC
        """,
        concept_id=concept_id,
    )
    return [dict(r) for r in results]


def get_terms_by_country(session, country: str) -> list:
    """Return all Terms for a given country ISO code."""
    results = session.run(
        """
        MATCH (t:Term {country: $country})
        RETURN
            t.concept_id  AS concept_id,
            t.source_id   AS source_id,
            t.source_name AS source_name,
            t.name        AS name,
            t.type        AS type,
            t.country     AS country,
            t.language    AS language,
            t.uploaded_at AS uploaded_at
        ORDER BY toLower(t.name) ASC
        """,
        country=country.strip().upper(),
    )
    return [dict(r) for r in results]


def get_terms_by_language(session, language: str) -> list:
    """Return all Terms for a given language (full name or ISO code)."""
    lang = resolve_language(language)
    results = session.run(
        """
        MATCH (t:Term)
        WHERE toLower(t.language) = toLower($language)
        RETURN
            t.concept_id  AS concept_id,
            t.source_id   AS source_id,
            t.source_name AS source_name,
            t.name        AS name,
            t.type        AS type,
            t.country     AS country,
            t.language    AS language,
            t.uploaded_at AS uploaded_at
        ORDER BY toLower(t.name) ASC
        """,
        language=lang,
    )
    return [dict(r) for r in results]


def get_sources(session) -> list:
    """Return all source names with their term counts and latest upload timestamp."""
    results = session.run(
        """
        MATCH (t:Term)
        WHERE t.source_name IS NOT NULL
        RETURN
            t.source_name          AS source_name,
            COUNT(t)               AS term_count,
            MAX(t.uploaded_at)     AS last_uploaded
        ORDER BY toLower(t.source_name) ASC
        """
    )
    return [dict(r) for r in results]


def get_terms_by_source(session, source_name: str) -> list:
    """Return all Terms from a specific source."""
    results = session.run(
        """
        MATCH (t:Term)
        WHERE toLower(t.source_name) = toLower($source_name)
        RETURN
            t.concept_id  AS concept_id,
            t.source_id   AS source_id,
            t.source_name AS source_name,
            t.name        AS name,
            t.type        AS type,
            t.country     AS country,
            t.language    AS language,
            t.uploaded_at AS uploaded_at
        ORDER BY toLower(t.name) ASC
        """,
        source_name=source_name,
    )
    return [dict(r) for r in results]


def get_countries(session) -> list:
    """Return all countries present in the database with their languages."""
    results = session.run(
        """
        MATCH (t:Term)
        WHERE t.country IS NOT NULL
        RETURN
            t.country              AS country,
            COLLECT(DISTINCT t.language) AS languages
        ORDER BY t.country ASC
        """
    )
    rows = []
    for r in results:
        langs = sorted(lg for lg in r["languages"] if lg)
        rows.append({"country": r["country"], "languages": langs})
    return rows


def get_languages(session) -> list:
    """Return all distinct languages present in the database."""
    results = session.run(
        """
        MATCH (t:Term)
        WHERE t.language IS NOT NULL
        RETURN DISTINCT t.language AS language
        ORDER BY t.language ASC
        """
    )
    return [r["language"] for r in results]


def reset_database(session) -> None:
    """Wipe every node and relationship from the database. Irreversible."""
    session.run("MATCH (n) DETACH DELETE n")


def language_exists(lang: str) -> bool:
    lang_resolved = resolve_language(lang)
    with driver.session() as session:
        result = session.run(
            "MATCH (t:Term) WHERE toLower(t.language) = toLower($lang) RETURN t LIMIT 1",
            lang=lang_resolved,
        ).single()
        return result is not None
