# Import dependencies
from codex.neo4j_driver import create_translation, get_translation_data, find_missing_translations, find_missing_brands, get_equivalent_brands, language_exists, resolve_to_base_term, driver
import json
import os

# Load language fallback rules from JSON configuration
CONFIG_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "config",
        "fallbacks.json"
    )
)

DEMO_PACKS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "demo_language_packs"
    )
)

with open(CONFIG_PATH, "r") as f:
    FALLBACK_LANGUAGES = json.load(f)

# Loads sample translation data into the Neo4j database dynamically from JSON files
# Used for testing, demos, and development
def load_demo_data(demo_dir: str = DEMO_PACKS_DIR):
    loaded = []
    if os.path.exists(demo_dir) and os.path.isdir(demo_dir):
        for filename in sorted(os.listdir(demo_dir)):
            if filename.endswith(".json"):
                file_path = os.path.join(demo_dir, filename)
                try:
                    result = load_language_pack(file_path)
                    loaded.append(result)
                except Exception as exc:
                    print(f"Failed to load demo pack {filename}: {exc}")
    return {"status": "Demo data added", "loaded": loaded}

def translate(term: str, lang: str = None, country: str = None):
    # Normalize input
    term = term.strip().lower()

    with driver.session() as session:
        # Resolve user input (canonical, translated, or fuzzy) to base term
        canonical, _ = resolve_to_base_term(session, term)
        if canonical:
            term = canonical.lower()
    
        # Tries requested language first
        if lang: 
            direct = get_translation_data(session, term, lang, country)
            if direct:
                return{
                    "canonical": term,
                    "requested_language": lang, 
                    "used_language": lang,
                    "fallback_used": False,
                    "results":[
                        {
                            "term": term,
                            "translation": r["translation"],
                            "language": r["language"],
                            "brand": r["brand"],
                            "country": r["country"]
                        }
                        for r in direct
                    ]
                }
    
        # Tries fall back languages (from JSON config)
        if lang:
            fallback_list = FALLBACK_LANGUAGES.get(lang, [])

            for fb_lang in fallback_list:
                fb_records = get_translation_data(session, term, fb_lang, country)
                if fb_records:
                    return{
                        "canonical": term, 
                        "requested_language": lang,
                        "used_language": fb_lang,
                        "fallback_used": True,
                        "fallback_type": "regional",
                        "fallback_chain": fallback_list,
                        "results": [
                            {
                                "term": term,
                                "translation": r["translation"],
                                "language": r["language"],
                                "brand": r["brand"],
                                "country": r["country"]
                            }
                            for r in fb_records
                        ]
                    }
        
        # Universal fallback to English
        english_records = get_translation_data(session, term, "en", country)
        if english_records:
            return {
                "canonical": term,
                "requested_language": lang,
                "used_language": "en",
                "fallback_used": True,
                "fallback_type": "global_english",
                "fallback_chain": ["en"],
                "results": [
                    {
                        "term": term,
                        "translation": r["translation"],
                        "language": r["language"],
                        "brand": r["brand"],
                        "country": r["country"]
                    }
                    for r in english_records
                ]
            }
        
        # Nothing found anywhere

        # Check if the language pack is missing from DB
        lang_missing = (lang is not None and not language_exists(lang))
        return {
            "canonical": term,
            "requested_language": lang,
            "used_language": None,
            "missing_language_pack": lang_missing,
            "results": [],
            "error": (
                f"No translations found. The language '{lang}' is not installed. "
                "You may need to download or load a language pack."
                if lang_missing
                else "No translations found in requested, fallback, or English."

            )
        }


# Performs a quality audit on a term:
# - Missing translations
# - Missing brand names
# - Equivalent brands across countries
def sync_translation_data(term: str):
    with driver.session() as session:
        #print(f"Checking term: {term}\n")

        missing_translations = find_missing_translations(session, term)
        print("Missing Translations: ")
        if missing_translations:
            for m in missing_translations:
                print(f" - {m['country']} ({m['country_name']}) -> {m['reason']}")
        else:
            print("All translations present")
        
        print("\nMissing Brand Names:")

        missing_brands = find_missing_brands(session, term)
        if missing_brands:
            for m in missing_brands:
                print(f" - {m['country']} ({m['country_name']}) -> {m['reason']}")
        else:
            print("All brand names present")
            
        print("\nEquivalent Brands Across Countries:")

        equivalents = get_equivalent_brands(session, term)
        for e in equivalents:
            print(f" - {e['brand']} ({e['country']} / {e['country_name']})")

# Loads a language pack from a JSON file into Neo4j
# Supports bulk insertion of translations and optional brands
def load_language_pack(path_to_json):
    with open(path_to_json, "r", encoding="utf-8") as file:
        pack = json.load(file)

    lang_code = pack["language"]["code"]
    lang_name = pack["language"]["name"]

    with driver.session() as session:
        for term in pack["terms"]:
            canonical = term["canonical"]

            for entry in term["entries"]:
                translation = entry["translation"]
                country = entry["country"]
                brand = entry.get("brand") # Could be None

                create_translation(
                    session,
                    canonical=canonical,
                    brand=brand,
                    country=country,
                    lang_code=lang_code,
                    lang_name=lang_name,
                    translation=translation
                )
    return f"Loaded language pack: {lang_name}"


