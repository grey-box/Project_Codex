#!/usr/bin/env python3

"""
ICD-11 Chapter 21 -> Neo4j (ultra-simple tree with run markers & rate limiting)

- Root node: Chapter 21 ("Symptoms, signs or clinical findings, not elsewhere classified")
- Children: all subcategories beneath it, recursively (directed tree)
- Node label: :ICD
- Relationship: :HAS_CHILD (parent -> child)
- Node props: id, code, title, ds   (ds = dataset tag like "ICD11-21:2024-01")
- Run marker: :Ingest {uid, dataset, release, startedAt, finishedAt, nodeCount, edgeCount}
  with (Ingest)-[:ROOT]->(Root ICD node)
"""

import os
import sys
import time
import uuid
import json
import math
import logging
from datetime import datetime, timezone
from collections import deque

import requests
from neo4j import GraphDatabase, WRITE_ACCESS
from dotenv import load_dotenv, find_dotenv

# --------------------
# Config / Env
# --------------------

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

FORCE = os.getenv("FORCE", "0") == "1"

# Rate limit (requests per minute). WHO ICD API typical limit is ~200 rpm.
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "200"))
MIN_INTERVAL_S = 60.0 / max(1, RATE_LIMIT_RPM)  # min seconds between requests

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("icd21_loader")

# Dataset tag that goes onto every :ICD node
DATASET = f"ICD11-21:{ICD_RELEASE_ID}"

# --------------------
# Neo4j schema (simple)
# --------------------

CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT icd_node_id IF NOT EXISTS FOR (n:ICD) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ingest_uid IF NOT EXISTS FOR (i:Ingest) REQUIRE i.uid IS UNIQUE",
]

UPSERT_NODE = """
MERGE (n:ICD {id: $id})
  ON CREATE SET n.code = $code, n.title = $title, n.ds = $ds
  ON MATCH  SET n.code = coalesce(n.code, $code),
              n.title = coalesce(n.title, $title),
              n.ds = $ds
"""




UPSERT_EDGE = """
MATCH (p:ICD {id: $parent})
MATCH (c:ICD {id: $child})
MERGE (p)-[:HAS_CHILD]->(c)
"""

CREATE_INGEST_START = """
CREATE (i:Ingest {
  uid: $uid,
  dataset: $dataset,
  release: $release,
  startedAt: $startedAt
})
RETURN i
"""

MARK_INGEST_DONE = """
MATCH (i:Ingest {uid: $uid})
SET i.finishedAt = $finishedAt,
    i.nodeCount = $nodeCount,
    i.edgeCount = $edgeCount
"""

LINK_INGEST_ROOT = """
MATCH (i:Ingest {uid: $uid})
MATCH (r:ICD {id: $rootId})
MERGE (i)-[:ROOT]->(r)
"""

CHECK_ALREADY_DONE = """
MATCH (i:Ingest {dataset: $dataset})
WHERE i.finishedAt IS NOT NULL
RETURN i LIMIT 1
"""

COUNT_NODES_EDGES_FOR_DATASET = """
MATCH (n:ICD {ds: $ds})
WITH count(n) AS n
MATCH (:ICD {ds: $ds})-[rel:HAS_CHILD]->(:ICD {ds: $ds})
RETURN n, count(rel) AS r
"""

DELETE_DATASET_EDGES = """
MATCH (:ICD {ds: $ds})-[r:HAS_CHILD]->(:ICD {ds: $ds})
DELETE r
"""

DELETE_DATASET_NODES = """
MATCH (n:ICD {ds: $ds})
DELETE n
"""

DELETE_DATASET_INGESTS = """
MATCH (i:Ingest {dataset: $ds})
DETACH DELETE i
"""

# --------------------
# API & helpers
# --------------------

class RateLimiter:
    """Simple spacing-based limiter to ~N requests/min, with 429/5xx backoff."""
    def __init__(self, min_interval_s: float):
        self.min_interval = min_interval_s
        self.last_ts = 0.0

    def wait(self):
        now = time.monotonic()
        delta = now - self.last_ts
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self.last_ts = time.monotonic()

limiter = RateLimiter(MIN_INTERVAL_S)

def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_token() -> str:
    limiter.wait()
    r = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": "icdapi_access"},
        auth=(ICD_CLIENT_ID, ICD_CLIENT_SECRET),
        timeout=30,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    log.debug("Obtained access token")
    return token

def headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "API-Version": API_VERSION,
        "Accept-Language": ACCEPT_LANGUAGE,
    }

def _respect_retry_after(r):
    """Sleep per Retry-After if present, otherwise exponential-ish fallback."""
    retry_after = r.headers.get("Retry-After")
    if retry_after:
        try:
            secs = float(retry_after)
            log.warning("Retry-After header: sleeping %.2fs", secs)
            time.sleep(secs)
            return
        except Exception:
            pass
    # fallback sleep
    time.sleep(2.5)

def get_json(url: str, token: str, params=None, max_retries=6):
    """GET with rate-limit pacing + retry on 429/5xx with backoff."""
    attempt = 0
    while True:
        attempt += 1
        limiter.wait()
        try:
            r = requests.get(url, headers=headers(token), params=params or {}, timeout=60)
            if r.status_code == 429:
                log.warning("HTTP 429 on %s (attempt %d/%d)", url, attempt, max_retries)
                _respect_retry_after(r)
                if attempt < max_retries:
                    continue
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            body = (e.response.text[:500] + "...") if getattr(e.response, "text", "") else ""
            log.warning("Request failed [%s] %s | status=%s | body=%.120s", url, e, status, body)
            if status in (429, 500, 502, 503, 504) and attempt < max_retries:
                _respect_retry_after(e.response if hasattr(e, "response") else r)
                continue
            raise

def extract_title(node: dict) -> str:
    t = node.get("title")
    if isinstance(t, dict):
        return t.get("@value", "") or ""
    if isinstance(t, str):
        return t
    return ""

def extract_code(node: dict) -> str:
    return node.get("code") or node.get("theCode") or ""

def ensure_node_min(token: str, item):
    """Return (id, code, title) for an item (link or partial obj)."""
    if isinstance(item, str):
        node = get_json(item, token, params={"properties": "code,title"})
        return item, extract_code(node), extract_title(node)
    if isinstance(item, dict):
        node_id = item.get("@id")
        code = extract_code(item)
        title = extract_title(item)
        if not node_id:
            return None, "", ""
        if not (code or title):
            node = get_json(node_id, token, params={"properties": "code,title"})
            return node_id, extract_code(node), extract_title(node)
        return node_id, code, title
    return None, "", ""

def get_children_array(node_json: dict):
    arr = node_json.get("child")
    if isinstance(arr, list) and arr:
        return arr
    arr = node_json.get("descendant")
    if isinstance(arr, list) and arr:
        return arr
    return []

def find_chapter_21(token: str) -> str | None:
    root = get_json(MMS_ROOT, token, params={"flat": "true"})
    for child in root.get("child", []):
        node_id, code, title = ensure_node_min(token, child)
        if not node_id:
            continue
        if code == "21" or ("Symptoms, signs" in (title or "")):
            return node_id
    return None

def fetch_full(token: str, node_id: str) -> dict:
    return get_json(node_id, token)

# --------------------
# Neo4j helpers
# --------------------

def ensure_constraints(sess):
    for q in CREATE_CONSTRAINTS:
        sess.run(q)

def upsert_node(sess, node_json: dict):
    node_id = node_json.get("@id")
    if not node_id:
        return
    sess.run(
        UPSERT_NODE,
        id=node_id,
        code=extract_code(node_json) or None,
        title=extract_title(node_json) or None,
        ds=DATASET,
    )

def upsert_edge(sess, parent_id: str, child_id: str):
    sess.run(UPSERT_EDGE, parent=parent_id, child=child_id)

def dataset_already_completed(sess) -> bool:
    rec = sess.run(CHECK_ALREADY_DONE, dataset=DATASET).single()
    return bool(rec)

def start_ingest(sess, uid: str, root_id: str, release: str):
    sess.run(CREATE_INGEST_START, uid=uid, dataset=DATASET,
             release=release, startedAt=utc_iso())
    sess.run(LINK_INGEST_ROOT, uid=uid, rootId=root_id)

def finish_ingest(sess, uid: str):
    rec = sess.run(COUNT_NODES_EDGES_FOR_DATASET, ds=DATASET).single()
    n = rec["n"] if rec and "n" in rec else 0
    r = rec["r"] if rec and "r" in rec else 0
    sess.run(MARK_INGEST_DONE, uid=uid, finishedAt=utc_iso(),
             nodeCount=n, edgeCount=r)
    return n, r

def delete_dataset(sess):
    log.warning("Deleting dataset %s (ingest markers, then ICD nodes)…", DATASET)
    sess.run("MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i", ds=DATASET)
    sess.run("MATCH (n:ICD {ds: $ds}) DETACH DELETE n", ds=DATASET)
    log.info("Dataset %s deleted", DATASET)

# --------------------
# BFS ingestion
# --------------------

def ingest_tree(token: str, sess, root_id: str):
    """
    BFS from root_id, inserting nodes and HAS_CHILD edges.
    Logs progress periodically, and keeps requests paced via RateLimiter.
    """
    q = deque([(root_id, None)])  # (node_id, parent_id)
    visited = set()

    processed_nodes = 0
    created_edges = 0
    last_log = time.monotonic()

    # initial fetch to ensure root present
    full = fetch_full(token, root_id)
    upsert_node(sess, full)

    while q:
        node_id, parent = q.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        ## insert edge to this node if it has a parent
        #if parent:
        #    upsert_edge(sess, parent, node_id)
        #    created_edges += 1

        # fetch node + upsert (do again for children case; MERGE is idempotent)
        full = fetch_full(token, node_id)
        upsert_node(sess, full)
        processed_nodes += 1

        # insert edge to this node if it has a parent
        if parent:
            upsert_edge(sess, parent, node_id)
            created_edges += 1

        # fetch one layer of children (lightweight) and queue them
        subtree = get_json(
            node_id, token,
            params={"include": "descendant", "depth": "1", "properties": "code,title"}
        )
        children = get_children_array(subtree)
        for child in children:
            cid, _, _ = ensure_node_min(token, child)
            if cid and cid not in visited:
                q.append((cid, node_id))

        # periodic progress log
        now = time.monotonic()
        if now - last_log >= 2.0:
            log.info(
                "Progress: nodes=%d edges=%d queue=%d visited=%d rpm=%d",
                processed_nodes, created_edges, len(q), len(visited), RATE_LIMIT_RPM
            )
            last_log = now

    # final summary in this function
    log.info("Traversal complete: processed_nodes=%d created_edges=%d", processed_nodes, created_edges)

def smoke_test(sess):
    log.debug("Running write smoke test…")
    sess.run("CREATE (:SmokeTest {ts: timestamp()})")
    c = sess.run("MATCH (s:SmokeTest) RETURN count(s) AS c").single()["c"]
    log.debug("SmokeTest count after create: %s", c)
    sess.run("MATCH (s:SmokeTest) DELETE s")
    return c

# --------------------
# Main
# --------------------

def main():
    log.info("Connecting to %s db=%s user=%s", NEO4J_URI, NEO4J_DB, NEO4J_USER)
    log.info("Dataset: %s | Release: %s | RPM limit: %d | FORCE=%s",
             DATASET, ICD_RELEASE_ID, RATE_LIMIT_RPM, FORCE)
    token = get_token()

    ch21_id = find_chapter_21(token)
    if not ch21_id:
        log.error("Could not find ICD-11 Chapter 21 node")
        sys.exit(2)

    ch21_full = fetch_full(token, ch21_id)
    title = extract_title(ch21_full) or "Chapter 21"
    code = extract_code(ch21_full) or "21"
    log.info("Found Chapter 21 root: [%s] %s | id=%s", code, title, ch21_id)



    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session(database=NEO4J_DB) as sess:
            sc = smoke_test(sess)
            log.info("Smoke test wrote/seen %s temp node(s) (expected >==1)", sc)

            ensure_constraints(sess)

            if dataset_already_completed(sess) and not FORCE:
                log.info("Ingest already completed for dataset %s. Set FORCE=1 to rebuild.", DATASET)
                return

            if FORCE:
                delete_dataset(sess)

            run_uid = str(uuid.uuid4())
            start_ingest(sess, run_uid, ch21_id, ICD_RELEASE_ID)
            # verify Ingest node exists now
            ingest_exists = sess.run(
                "MATCH (i:Ingest {uid:$uid}) RETURN count(i) AS c", uid=run_uid
            ).single()["c"]
            log.info("Ingest node created? count=%s", ingest_exists)

            t0 = time.time()
            ingest_tree(token, sess, ch21_id)
            n, r = finish_ingest(sess, run_uid)
            dt = time.time() - t0
            log.info("DONE | dataset=%s uid=%s nodes=%d edges=%d elapsed=%.1fs",
                 DATASET, run_uid, n, r, dt)

    finally:
        driver.close()

if __name__ == "__main__":
    main()


