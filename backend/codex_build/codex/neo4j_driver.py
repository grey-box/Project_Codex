# Import dependencies
from neo4j import GraphDatabase       # Python driver from Neo4j
from dotenv import load_dotenv        # Loads environment variables from .env file
import os                             # Access to OS environment variables

# Loads environment varibles 
load_dotenv()

# Get Neo4j connection info
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

# Connect to Neo4j
driver = GraphDatabase.driver(uri, auth=(user, password))

# Create or update translation nodes for any medical term (medication and symtom)
def create_translation(session, canonical, brand, country, lang_code, lang_name, translation, term_type="medication"):

    # Core translation structure
    query = """
    MERGE (t:Term {canonical:$canonical, type:$term_type})
    MERGE (l:Language {code:$lang_code, name:$lang_name})
    MERGE (tr:Translation {text:$translation, country:$country})
    MERGE (tr)-[:OF_TERM]->(t)
    MERGE (tr)-[:IN_LANGUAGE]->(l)
    MERGE (c:Country {iso2:$country, name:$country})
    MERGE (tr)-[:USED_IN]->(c)
    """

    session.run(query, canonical=canonical, country=country, lang_code=lang_code, lang_name=lang_name, translation=translation, term_type=term_type)

    # If there's no brand for term from a country
    if brand is not None:
        query = """
        MATCH (t:Term {canonical:$canonical})
        MATCH (tr:Translation)-[:OF_TERM]->(t)
        WHERE tr.text = $translation AND tr.country = $country
        MATCH (c:Country {iso2:$country})
        MERGE (b:Brand {name:$brand})
        MERGE (b)-[:SOLD_IN]->(c)
        MERGE (tr)-[:HAS_BRAND]->(b)
        MERGE (t)-[:SOLD_AS]->(b)
        MERGE (b)-[:CONTAINS]->(t)
        """
        session.run(query, canonical=canonical, translation=translation, country=country, brand=brand)

    # Just for comfirmation in console for verification
    print(f"Added {canonical} → {translation} ({lang_name}) / Brand: {brand} in {country}")

# Retrieves all translations and related info for a given term
def get_translation_data(session, canonical, lang, country):
    query = """
    MATCH (t:Term)
    WHERE t.canonical IS NOT NULL 
      AND (
        t.canonical = $canonical 
        OR apoc.text.jaroWinklerDistance(t.canonical, $canonical) < 0.20
      )
    MATCH (tr:Translation)-[:OF_TERM]->(t)
    MATCH (tr)-[:IN_LANGUAGE]->(l:Language)
    OPTIONAL MATCH (tr)-[:USED_IN]->(c:Country)
    OPTIONAL MATCH (tr)-[:HAS_BRAND]->(b:Brand)
    WHERE ($lang IS NULL OR l.code = $lang)
      AND ($country IS NULL OR c.iso2 = $country)
    RETURN DISTINCT
        tr.text AS translation, 
        l.name AS language,
        b.name AS brand, 
        l.code AS lang_code,
        c.iso2 AS country,
        c.name AS country_name
    ORDER BY language, country
    """
    
    result = session.run(query, canonical=canonical, lang=lang, country=country)
    return [r.data() for r in result]

# Finds countries where this term has no translation
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
        if len(row["translations"]) == 0 or row["translations"] == [None]:
            missing.append(
                {
                    "country": row["country"],
                    "country_name": row["country_name"],
                    "reason": "No translation found for this country"
                }
            )
    return missing

# Finds countries where this medication term lacks a brand name
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
        if row["brands"] == [] or row["brands"] == [None]:
            missing.append(
                {
                    "country": row["country"],
                    "country_name": row["country_name"],
                    "reason": "No brand name found",
                }
            )
    return missing


# Returns all brand names for a medication across countries
# Shows brand equivalence between countries
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

# Resolves any input (canonical, translated, or fuzzy) to a base canonical term
def resolve_to_base_term(session, term): 
    query = """
    CALL {
        MATCH (t:Term)
        WHERE t.canonical = $term
        RETURN t.canonical AS brand, t.canonical AS base
        UNION
        MATCH (t:Term)<-[:CONTAINS]-(b:Brand)
        WHERE b.name = $term
        RETURN b.name AS brand, t.canonical AS base
        UNION
        MATCH (t:Term)<-[:OF_TERM]-(tr:Translation)
        WHERE tr.text = $term
        RETURN t.canonical AS brand, t.canonical AS base
        UNION
        MATCH (t:Term)
        WHERE apoc.text.jaroWinklerDistance(toLower(t.canonical), toLower($term)) < 0.20
        RETURN t.canonical AS brand, t.canonical AS base
        UNION
        MATCH (t:Term)<-[:CONTAINS]-(b:Brand)
        WHERE apoc.text.jaroWinklerDistance(toLower(b.name), toLower($term)) < 0.20
        RETURN b.name AS brand, t.canonical AS base
        UNION
        MATCH (t:Term)<-[:OF_TERM]-(tr:Translation)
        WHERE apoc.text.jaroWinklerDistance(toLower(tr.text), toLower($term)) < 0.20
        RETURN t.canonical AS brand, t.canonical AS base
    }
    WITH collect({brand: brand, base: base}) AS results
    WITH results, any(r IN results WHERE r.brand = r.base) AS exactMatch
    UNWIND results AS row
    WITH row, exactMatch
    WHERE exactMatch = false OR row.brand = row.base
    RETURN row.brand AS brand, row.base AS base
    """

    result = session.run(query, term=term).single()
    if not result:
        return None
    elif (result["base"] == result["brand"]):
        return result["base"], None
    else:
        return result["base"], result["brand"]
        

# Checks whether a language pack exists in the database
def language_exists(lang_code: str) -> bool:
    with driver.session() as session:
        result = session.run(
            "MATCH (l:Language {code:$code}) RETURN l LIMIT 1",
            code=lang_code
        ).single()
        return result is not None

# Retrieves all brands associated with a term across countries
def get_brands_for_term(session, term):
    query = """
    MATCH (t:Term)
    WHERE t.canonical = $term
        OR apoc.text.jaroWinklerDistance(toLower(t.canonical), toLower($term)) < 0.20
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

# Retrieves all countries associated with a term
def get_countries_for_term(session, term):
    query = """
    MATCH (t:Term)
    WHERE t.canonical = $term
        OR apoc.text.jaroWinklerDistance(toLower(t.canonical), toLower($term)) < 0.20
    MATCH (tr:Translation)-[:OF_TERM]->(t)
    WHERE toLower(tr.text) = toLower(t.canonical)
    RETURN collect(DISTINCT tr.country) AS country
    ORDER BY country
    """

    result = session.run(query, term=term)
    countries = result.single().value() if result.peek() else []
    countries = ', '.join(countries)
    return countries

# Retrieves all languages associated with a term
def get_languages_for_term(session, term):
    query = """
    MATCH (t:Term)
    WHERE t.canonical = $term
        OR apoc.text.jaroWinklerDistance(toLower(t.canonical), toLower($term)) < 0.20
    MATCH (tr:Translation)-[:OF_TERM]->(t)
    WHERE toLower(tr.text) = toLower(t.canonical)
    MATCH (tr)-[:IN_LANGUAGE]->(l:Language)
    RETURN collect(DISTINCT toUpper(l.code)) AS language
    ORDER BY language
    """

    result = session.run(query, term=term)
    languages = result.single().value() if result.peek() else []
    languages = ', '.join(languages)
    return languages

# Retrieves all countries associated with a brand
def get_countries_for_brand(session, term):
    query = """
    MATCH (b:Brand)
    WHERE b.name = $term
        OR apoc.text.jaroWinklerDistance(toLower(b.name), toLower($term)) < 0.20
    MATCH (tr:Translation)-[:HAS_BRAND]->(b)
    RETURN collect(DISTINCT tr.country) AS country
    ORDER BY country
    """

    result = session.run(query, term=term)
    countries = result.single().value() if result.peek() else []
    countries = ', '.join(countries)
    return countries

# Retrieves all languages associated with a brand
def get_languages_for_brand(session, term):
    query = """
    MATCH (b:Brand)
    WHERE b.name = $term
        OR apoc.text.jaroWinklerDistance(toLower(b.name), toLower($term)) < 0.20
    MATCH (tr:Translation)-[:HAS_BRAND]->(b)
    MATCH (tr)-[:IN_LANGUAGE]->(l:Language)
    RETURN collect(DISTINCT toUpper(l.code)) AS language
    ORDER BY language
    """

    result = session.run(query, term=term)
    languages = result.single().value() if result.peek() else []
    languages = ', '.join(languages)
    return languages