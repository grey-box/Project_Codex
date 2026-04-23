from codex.neo4j_driver import translate_term, driver


def translate(term: str, source_lang: str, target_lang: str,
              target_country: str = None, source_name: str = None) -> dict:
    """
    Translate a drug name from source_lang into target_lang.

    term           : drug name to look up
    source_lang    : language of the input term (ISO code or full name)
    target_lang    : desired output language (ISO code or full name)
    target_country : optional ISO country code to narrow results
    source_name    : optional source name filter (e.g. "RxNorm")
    """
    with driver.session() as session:
        results = translate_term(
            session, term, source_lang, target_lang,
            target_country=target_country,
            source_name=source_name,
        )

    return {
        "term":           term,
        "source_lang":    source_lang,
        "target_lang":    target_lang,
        "target_country": target_country,
        "source_name":    source_name,
        "found":          bool(results),
        "results":        results,
    }
