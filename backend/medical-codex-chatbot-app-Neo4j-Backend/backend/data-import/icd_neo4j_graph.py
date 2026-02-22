#!/usr/bin/env python3
"""
Small demo combining API query with Neo4j graph.
"""

import os
import sys
import json
from collections import deque

import requests
from neo4j import GraphDatabase
from dotenv import load_dotenv, find_dotenv

# Config

env_path = find_dotenv(usecwd=True)
if not env_path:
    print("ERROR: .env not found at repo root")
    sys.exit(1)
load_dotenv(env_path)

ICD_CLIENT_ID = os.getenv("ICD_CLIENT_ID")
ICD_CLIENT_SECRET = os.getenv("ICD_CLIENT_SECRET")
if not ICD_CLIENT_ID or not ICD_CLIENT_SECRET:
    print("ERROR: Missing ICD_CLIENT_ID or ICD_CLIENT_SECRET in .env")
    sys.exit(1)

API_VERSION = "v2"
ACCEPT_LANGUAGE = "en"
ICD_RELEASE_ID = os.getenv("ICD_RELEASE_ID", "2024-01")

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
ICD_BASE = "https://id.who.int/icd"
MMS_BASE = f"{ICD_BASE}/release/11/{ICD_RELEASE_ID}"
MMS_ROOT = f"{MMS_BASE}/mms"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

SEED_PEOPLE_MOVIE_DEMO = False

# ICD API Functions

def get_token():
    r = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": "icdapi_access"},
        auth=(ICD_CLIENT_ID, ICD_CLIENT_SECRET),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]

def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "API-Version": API_VERSION,
        "Accept-Language": ACCEPT_LANGUAGE,
    }

def get_json(url, token, params=None):
    r = requests.get(url, headers=headers(token), params=params or {}, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("Request failed", url)
        print("Status", r.status_code)
        print("Body", r.text[:800])
        raise
    return r.json()

def extract_title(node):
    t = node.get("title")
    if isinstance(t, dict):
        return t.get("@value", "")
    if isinstance(t, str):
        return t
    return ""

def extract_code(node):
    return node.get("code") or node.get("theCode") or ""

def extract_def(node):
    d = node.get("definition") or node.get("briefDefinition")
    if isinstance(d, dict):
        return d.get("@value", "")
    if isinstance(d, str):
        return d
    return ""

def ensure_node_min(token, item):
    """Return (id, code, title, node_json_min) for an item which might be a link or a partial obj."""
    if isinstance(item, str):
        node_id = item
        node = get_json(node_id, token, params={"properties": "code,title"})
        return node_id, extract_code(node), extract_title(node), node
    if isinstance(item, dict):
        node_id = item.get("@id")
        code = extract_code(item)
        title = extract_title(item)
        if not node_id:
            return None, "", "", {}
        if not (code or title):
            node = get_json(node_id, token, params={"properties": "code,title"})
            return node_id, extract_code(node), extract_title(node), node
        return node_id, code, title, item
    return None, "", "", {}

def get_children_array(node_json):
    arr = node_json.get("child")
    if isinstance(arr, list) and arr:
        return arr
    arr = node_json.get("descendant")
    if isinstance(arr, list) and arr:
        return arr
    return []

def find_chapter_21(token):
    root = get_json(MMS_ROOT, token, params={"flat": "true"})
    for child in root.get("child", []):
        node_id, code, title, _ = ensure_node_min(token, child)
        if not node_id:
            continue
        if code == "21" or ("Symptoms, signs" in (title or "")):
            return node_id
    return None

def bfs_children_ids(token, node_id):
    # get direct children ids
    subtree = get_json(
        node_id, token,
        params={"include": "descendant", "depth": "1", "properties": "code,title"}
    )
    out = []
    for child in get_children_array(subtree):
        cid, _, _, _ = ensure_node_min(token, child)
        if cid:
            out.append(cid)
    return out

def fetch_node_full(token, node_id):
    return get_json(node_id, token)

# Neo4j

CONSTRAINTS = [
    "CREATE CONSTRAINT icd_node_id IF NOT EXISTS FOR (n:ICD) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT icd_code IF NOT EXISTS FOR (n:ICD) REQUIRE n.code IS UNIQUE",
    # Demo labels
    "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
    "CREATE CONSTRAINT movie_title IF NOT EXISTS FOR (m:Movie) REQUIRE m.title IS UNIQUE",
]

UPSERT_ICD_NODE = """
MERGE (n:ICD {id: $id})
  ON CREATE SET
    n.code = $code,
    n.title = $title,
    n.kind  = $kind,
    n.source = $source
  ON MATCH SET
    n.code  = coalesce(n.code,  $code),
    n.title = coalesce(n.title, $title),
    n.kind  = coalesce(n.kind,  $kind),
    n.source = coalesce(n.source, $source)
"""

UPSERT_ICD_EDGE = """
MATCH (p:ICD {id: $parent})
MATCH (c:ICD {id: $child})
MERGE (p)-[:HAS_CHILD]->(c)
"""

PEOPLE_MOVIE_DEMO = """
MERGE (p1:Person {name: $alice})
MERGE (p2:Person {name: $bob})
MERGE (m:Movie  {title: $movie, released: 1999})
MERGE (p1)-[:KNOWS]->(p2)
MERGE (p1)-[:ACTED_IN {role: "Lead"}]->(m)
MERGE (p2)-[:ACTED_IN {role: "Sidekick"}]->(m)
"""

SUMMARY_COUNTS = """
MATCH (n:ICD) RETURN count(n) AS nodes
"""

SUMMARY_EDGES = """
MATCH (:ICD)-[r:HAS_CHILD]->(:ICD) RETURN count(r) AS rels
"""

SHOW_SAMPLE_PATHS = """
MATCH p = (root:ICD)-[:HAS_CHILD*1..3]->(leaf:ICD)
WHERE root.code = "21" OR root.title CONTAINS "Symptoms"
RETURN p LIMIT 5
"""

# Loader

def icd_kind(node):
    """Derive a simple 'kind' string for display (best-effort)."""
    t = node.get("@type")
    if isinstance(t, list) and t:
        return t[-1] if isinstance(t[-1], str) else "ICDEntity"
    if isinstance(t, str):
        return t
    return "ICDEntity"

def ensure_constraints(sess):
    for q in CONSTRAINTS:
        sess.run(q)

def upsert_icd_node(sess, node_json):
    node_id = node_json.get("@id")
    if not node_id:
        return
    sess.run(
        UPSERT_ICD_NODE,
        id=node_id,
        code=extract_code(node_json) or None,
        title=extract_title(node_json) or None,
        kind=icd_kind(node_json),
        source="ICD-11 API",
    )

def upsert_icd_edge(sess, parent_id, child_id):
    sess.run(UPSERT_ICD_EDGE, parent=parent_id, child=child_id)

def seed_people_movie(sess):
    sess.run(PEOPLE_MOVIE_DEMO, alice="Alice", bob="Bob", movie="The Matrix-ish Demo")

def ingest_icd_subtree(token, sess, start_id):
    """BFS the subtree beginning at start_id, insert nodes & edges."""
    q = deque([(start_id, None)])  # (node_id, parent_id)
    visited = set()
    while q:
        node_id, parent = q.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        full = fetch_node_full(token, node_id)
        upsert_icd_node(sess, full)
        if parent:
            upsert_icd_edge(sess, parent, node_id)

        for cid in bfs_children_ids(token, node_id):
            if cid not in visited:
                q.append((cid, node_id))

def main():
    token = get_token()

    ch21_id = find_chapter_21(token)
    if not ch21_id:
        print("Could not locate Chapter 21")
        sys.exit(2)

    first_layer = get_json(
        ch21_id, token,
        params={"include": "descendant", "depth": "1", "properties": "code,title"}
    )
    children = get_children_array(first_layer)
    print("First layer under Chapter 21:")
    for i, child in enumerate(children, start=1):
        _, code, title, _ = ensure_node_min(token, child)
        label = f"{title or ''} [{code}]" if code else title
        print(f"  {i:02d}. {label}")

    if not children:
        print("No first layer items found — nothing to ingest.")
        return

    start_id, _, start_title, _ = ensure_node_min(token, children[0])
    print(f"\nIngesting subtree starting at: {start_title or start_id}\n")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session(database=NEO4J_DB) as sess:
            ensure_constraints(sess)

            ch21_full = fetch_node_full(token, ch21_id)
            upsert_icd_node(sess, ch21_full)

            upsert_icd_edge(sess, ch21_id, start_id)

            ingest_icd_subtree(token, sess, start_id)

            if SEED_PEOPLE_MOVIE_DEMO:
                seed_people_movie(sess)

            n = sess.run(SUMMARY_COUNTS).single()["nodes"]
            r = sess.run(SUMMARY_EDGES).single()["rels"]
            print(f"Inserted/updated ICD nodes: {n}")
            print(f"Inserted/updated HAS_CHILD relationships: {r}")

            print("\nSample paths (up to depth 3) under Chapter 21:")
            for rec in sess.run(SHOW_SAMPLE_PATHS):
                nodes = []
                for node in rec["p"].nodes:
                    code = node.get("code") or ""
                    title = node.get("title") or ""
                    nodes.append(f'[{code}] {title}'.strip())
                print("  " + "  ->  ".join(nodes))
    finally:
        driver.close()

if __name__ == "__main__":
    main()

