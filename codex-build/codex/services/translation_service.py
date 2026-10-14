from codex.neo4j_driver import (
    translate_drug,
    find_missing_translations,
    find_missing_brands,
    get_equivalent_brands,
    resolve_to_base_term,
    language_exists,
    driver,
)


def translate(term: str, source_lang: str, target_lang: str,
              country: str = None) -> dict:
    """
    Translate a drug name from source_lang into target_lang.

    Parameters
    ----------
    term        : drug name — generic (Ibuprofen) or brand (Advil)
    source_lang : ISO 639-1 code of the input language  (e.g. "en")
    target_lang : ISO 639-1 code of the desired language (e.g. "es")
    country     : ISO 3166-1 alpha-2 to narrow results (e.g. "MX") — optional

    Returns a dict with metadata + a `results` list sorted by generic_name
    then brand_name.  Each result row has:
        brand_name, generic_name, original_language, translated_language
    """
    with driver.session() as session:
        results = translate_drug(session, term, source_lang, target_lang, country)

    return {
        "term":        term,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "country":     country,
        "found":       bool(results),
        "results":     results,
    }


def sync_translation_data(term: str):
    """Quality audit — prints missing translations, brands, and equivalents."""
    with driver.session() as session:
        missing_translations = find_missing_translations(session, term)
        print("Missing Translations:")
        for m in missing_translations:
            print(f"  - {m['country']} ({m['country_name']}) → {m['reason']}")
        if not missing_translations:
            print("  All translations present")

        missing_brands = find_missing_brands(session, term)
        print("\nMissing Brand Names:")
        for m in missing_brands:
            print(f"  - {m['country']} ({m['country_name']}) → {m['reason']}")
        if not missing_brands:
            print("  All brand names present")

        equivalents = get_equivalent_brands(session, term)
        print("\nEquivalent Brands Across Countries:")
        for e in equivalents:
            print(f"  - {e['brand']} ({e['country']} / {e['country_name']})")
