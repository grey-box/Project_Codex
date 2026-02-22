# neo4j_demo.py
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"   # WSL Neo4j
USER = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def setup_constraints(session):
    session.run("CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE")
    session.run("CREATE CONSTRAINT movie_title IF NOT EXISTS FOR (m:Movie) REQUIRE m.title IS UNIQUE")

def create_demo_graph(session):
    session.run("""
    MERGE (p1:Person {name: $alice})
    MERGE (p2:Person {name: $bob})
    MERGE (m:Movie  {title: $movie, released: 1999})
    MERGE (p1)-[:KNOWS]->(p2)
    MERGE (p1)-[:ACTED_IN {role: "Lead"}]->(m)
    MERGE (p2)-[:ACTED_IN {role: "Sidekick"}]->(m)
    """, alice="Alice", bob="Bob", movie="The Matrix-ish Demo")

def read_back(session):
    result = session.run("""
    MATCH (p:Person)-[r:ACTED_IN]->(m:Movie)
    RETURN p.name AS person, r.role AS role, m.title AS movie
    ORDER BY person
    """)
    for row in result:
        print(f'{row["person"]} acted as {row["role"]} in "{row["movie"]}"')

def main():
    # Just open a session to the default db
    with driver.session(database="neo4j") as session:
        setup_constraints(session)
        create_demo_graph(session)
        read_back(session)

if __name__ == "__main__":
    main()
    driver.close()

