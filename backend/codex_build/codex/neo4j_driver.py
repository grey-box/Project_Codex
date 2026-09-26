# Import dependencies
from neo4j import GraphDatabase       # Python driver from Neo4j
from dotenv import load_dotenv        # Loads environment variables from .env file
import os                             # Access to OS environment variables
import bcrypt                         # Used for hashing passwords

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

# Searches for canonical terms given any input (canonical, translated, or fuzzy)
def search_database(session, term): 
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
    UNWIND results AS row
    RETURN row.brand AS brand, row.base AS base
    """

    results = session.run(query, term=term)
    if not results:
        return None
    
    results_array = []
    for result in results:
        if (result["base"].lower() == term.lower()):
            results_array.append([result["base"], None])
            return results_array
        
        if (result["base"] == result["brand"]):
            results_array.append([result["base"], None])
        else:
            results_array.append([result["base"], result["brand"]])
    return results_array

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

# Requires all user emails to be unique
def init_user_constraints(session):
    query = """
    CREATE CONSTRAINT user_email_unique IF NOT EXISTS
    FOR (u:User) REQUIRE u.email IS UNIQUE
    """
    session.run(query)
    
# Utility to hash passwords
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

# Creates a new User node with a hashed password
def create_user(session, real_name, password, role, affiliation, email):
    hashed_pwd = hash_password(password)
    query = """
    CREATE (u:User {
        email: $email,
        real_name: $real_name,
        password: $password,
        role: $role,
        affiliation: $affiliation,
        created_at: datetime()
    })
    RETURN u.email AS email, u.real_name AS real_name, u.role AS role, u.affiliation AS affiliation
    """
    result = session.run(
        query, 
        email=email.lower().strip(), 
        real_name=real_name, 
        password=hashed_pwd, 
        role=role, 
        affiliation=affiliation
    )
    record = result.single()
    if record:
        print(f"User created: {record['email']}")
        return record.data()
    return None

# Retrieves a single user by their unique email (omits password hash from return)
def get_user_by_email(session, email):
    query = """
    MATCH (u:User {email: $email})
    RETURN u.email AS email, u.real_name AS real_name, u.role AS role, u.affiliation AS affiliation, u.created_at AS created_at
    """
    result = session.run(query, email=email.lower().strip()).single()
    return result.data() if result else None

# Retrieves a list of all users
def get_all_users(session, limit=100):
    query = """
    MATCH (u:User)
    RETURN u.email AS email, u.real_name AS real_name, u.role AS role, u.affiliation AS affiliation
    LIMIT $limit
    """
    result = session.run(query, limit=limit)
    return [record.data() for record in result]

# Dynamically updates user fields based on provided arguments
def update_user(session, email, real_name=None, role=None, affiliation=None, password=None):
    updates = []
    params = {"email": email.lower().strip()}

    if real_name is not None:
        updates.append("u.real_name = $real_name")
        params["real_name"] = real_name
    if role is not None:
        updates.append("u.role = $role")
        params["role"] = role
    if affiliation is not None:
        updates.append("u.affiliation = $affiliation")
        params["affiliation"] = affiliation
    if password is not None:
        updates.append("u.password = $password")
        params["password"] = hash_password(password)

    if not updates:
        print("No fields provided to update.")
        return None

    set_clause = ", ".join(updates)
    query = f"""
    MATCH (u:User {{email: $email}})
    SET {set_clause}, u.updated_at = datetime()
    RETURN u.email AS email, u.real_name AS real_name, u.role AS role, u.affiliation AS affiliation
    """
    
    result = session.run(query, **params).single()
    return result.data() if result else None

# Deletes a user node by email and removes any connected relationships (DETACH DELETE)
def delete_user(session, email):
    """."""
    query = """
    MATCH (u:User {email: $email})
    DETACH DELETE u
    RETURN count(u) AS deleted_count
    """
    result = session.run(query, email=email.lower().strip()).single()
    deleted = result["deleted_count"] > 0
    if deleted:
        print(f"Successfully deleted user: {email}")
    else:
        print(f"No user found with email: {email}")
    return deleted

# Retrieves only the role assigned to a specific user
def get_user_role(session, email: str) -> str | None:
    query = """
    MATCH (u:User {email: $email})
    RETURN u.role AS role
    """
    result = session.run(query, email=email.lower().strip()).single()
    return result["role"] if result else None

# Retrieves all users matching a specific role
def get_users_by_role(session, role: str) -> list[dict]:
    query = """
    MATCH (u:User {role: $role})
    RETURN u.email AS email, u.real_name AS real_name, u.affiliation AS affiliation
    ORDER BY u.real_name
    """
    result = session.run(query, role=role)
    return [record.data() for record in result]

# Updates the role for a specific user and logs the updated timestamp
def update_user_role(session, email: str, new_role: str) -> dict | None:
    query = """
    MATCH (u:User {email: $email})
    SET u.role = $new_role, u.updated_at = datetime()
    RETURN u.email AS email, u.real_name AS real_name, u.role AS role
    """
    result = session.run(
        query, 
        email=email.lower().strip(), 
        new_role=new_role
    ).single()
    
    if result:
        print(f"Updated role for {email} to '{new_role}'")
        return result.data()
    
    print(f"User with email '{email}' not found.")
    return None