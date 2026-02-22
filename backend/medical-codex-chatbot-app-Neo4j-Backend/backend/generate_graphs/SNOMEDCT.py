#!/usr/bin/env python3

"""
SNOMED CT (Clinical finding hierarchy) -> Neo4j (simple tree with run markers & rate limiting)

- Root concept: 404684003 |Clinical finding|
- Label: :SNOMED
- Relationship: :HAS_CHILD (parent -> child)
- Node props: id, code, title, ds   (ds = dataset tag like "SNOMEDCT:MAIN:2025-07-31")
- Run marker: :Ingest {uid, dataset, release, startedAt, finishedAt, nodeCount, edgeCount}
  with (Ingest)-[:ROOT]->(Root SNOMED node)
"""

import os
import sys
import time
import uuid
import json
import logging
from datetime import datetime, timezone
from collections import deque

import requests
from neo4j import GraphDatabase, WRITE_ACCESS
from dotenv import load_dotenv, find_dotenv

# --------------------
# Env
# --------------------

# TODO document environment variables in more depth (Create wiki for all graph generations?)
# Note a lot of code reused from prior graph generations

env_path = find_dotenv(usecwd=True)
if not env_path:
    print("ERROR: .env not found at repo root")
    sys.exit(1)
load_dotenv(env_path)

SNOWSTORM_BASE = os.getenv("SNOWSTORM_BASE", "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct")
SNOMED_BRANCH = os.getenv("SNOMED_BRANCH", "MAIN")  # USING MAIN/SNOMEDCT-US
SNOMED_ROOT_ID = os.getenv("SNOMED_ROOT_ID", "404684003")  # Clinical finding
SNOMED_RELEASE = os.getenv("SNOMED_RELEASE", "")

ACCEPT_LANGUAGE = os.getenv("ACCEPT_LANGUAGE", "en")
API_TIMEOUT_S = int(os.getenv("API_TIMEOUT_S", "60"))

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

FORCE = os.getenv("FORCE", "0") == "1"

RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "200"))
MIN_INTERVAL_S = 60.0 / max(1, RATE_LIMIT_RPM)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("snomed_loader")

# dataset tag (can adjust)
DATASET = f"SNOMEDCT:{SNOMED_BRANCH}:{SNOMED_RELEASE or 'latest'}"

# --------------------
# Neo4j
# --------------------

CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT snomed_node_id IF NOT EXISTS FOR (n:SNOMED) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ingest_uid IF NOT EXISTS FOR (i:Ingest) REQUIRE i.uid IS UNIQUE",
]

UPSERT_NODE = """
MERGE (n:SNOMED {id: $id})
  ON CREATE SET n.code = $code, n.title = $title, n.ds = $ds
  ON MATCH  SET n.code = coalesce(n.code, $code),
              n.title = coalesce(n.title, $title),
              n.ds = $ds
"""

UPSERT_EDGE = """
MATCH (p:SNOMED {id: $parent})
MATCH (c:SNOMED {id: $child})
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
MATCH (r:SNOMED {id: $rootId})
MERGE (i)-[:ROOT]->(r)
"""

CHECK_ALREADY_DONE = """
MATCH (i:Ingest {dataset: $dataset})
WHERE i.finishedAt IS NOT NULL
RETURN i LIMIT 1
"""

COUNT_NODES_EDGES_FOR_DATASET = """
MATCH (n:SNOMED {ds: $ds})
WITH count(n) AS n
MATCH (:SNOMED {ds: $ds})-[rel:HAS_CHILD]->(:SNOMED {ds: $ds})
RETURN n, count(rel) AS r
"""

# --------------------
# API
# --------------------

class RateLimiter:
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

def headers():
    return {
        "Accept": "application/json",
        "Accept-Language": ACCEPT_LANGUAGE,
    }

def _respect_retry_after(r):
    ra = r.headers.get("Retry-After")
    if ra:
        try:
            secs = float(ra); log.warning("Retry-After: sleeping %.2fs", secs); time.sleep(secs); return
        except Exception:
            pass
    time.sleep(2)

def get_json(url: str, params=None, max_retries=6):
    attempt = 0
    while True:
        attempt += 1
        limiter.wait()
        try:
            r = requests.get(url, headers=headers(), params=params or {}, timeout=API_TIMEOUT_S)
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

# Snowstorm helpers

def api(path: str) -> str:
    base = SNOWSTORM_BASE.rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}"

def fetch_concept(concept_id: str) -> dict:
    # /browser/{branch}/concepts/{conceptId}
    return get_json(api(f"browser/{SNOMED_BRANCH}/concepts/{concept_id}"))

def fetch_children(concept_id: str) -> list:
    # /browser/{branch}/concepts/{conceptId}/children
    data = get_json(api(f"browser/{SNOMED_BRANCH}/concepts/{concept_id}/children"))
    if isinstance(data, list):
        return data
    return data.get("items", []) if isinstance(data, dict) else []

def resolve_release() -> str:
    if SNOMED_RELEASE:
        return SNOMED_RELEASE
    try:
        # codesystem versions are newest-first typically
        versions = get_json(api("codesystems/SNOMEDCT/versions"))
        items = versions.get("items") if isinstance(versions, dict) else versions
        if items:
            v = items[0]
            return v.get("version") or v.get("effectiveDate") or "latest"
    except Exception:
        pass
    return "latest"

# extractors

def extract_title(node: dict) -> str:
    # prefer preferred term, fall back to FSN
    pt = (((node or {}).get("pt") or {}).get("term"))
    fsn = (((node or {}).get("fsn") or {}).get("term"))
    term = pt or fsn
    if not term:
        term = node.get("term") if isinstance(node.get("term"), str) else None
    return term or ""

def extract_code(node: dict) -> str:
    return (node or {}).get("conceptId") or ""

# --------------------
# Neo4j helpers
# --------------------

def ensure_constraints(sess):
    for q in CREATE_CONSTRAINTS:
        sess.run(q)

def upsert_node(sess, node_json: dict):
    cid = extract_code(node_json)
    if not cid:
        return
    sess.run(
        UPSERT_NODE,
        id=cid,
        code=cid,
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
    log.warning("Deleting dataset %s…", DATASET)
    sess.run("MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i", ds=DATASET)
    sess.run("MATCH (n:SNOMED {ds: $ds}) DETACH DELETE n", ds=DATASET)
    log.info("Dataset %s deleted", DATASET)

# --------------------
# BFS ingest
# --------------------

def ingest_tree(sess, root_id: str):
    q = deque([(root_id, None)])
    visited = set()
    processed = 0
    created_edges = 0
    last_log = time.monotonic()

    root_full = fetch_concept(root_id)
    upsert_node(sess, root_full)

    while q:
        cid, parent = q.popleft()
        if cid in visited:
            continue
        visited.add(cid)

        full = fetch_concept(cid)
        upsert_node(sess, full)
        processed += 1

        if parent:
            upsert_edge(sess, parent, cid)
            created_edges += 1

        for child in fetch_children(cid):
            child_id = extract_code(child) or child.get("id")
            if child_id and child_id not in visited:
                q.append((child_id, cid))

        now = time.monotonic()
        if now - last_log >= 2.0:
            log.info("Progress: nodes=%d edges=%d queue=%d visited=%d rpm=%d",
                     processed, created_edges, len(q), len(visited), RATE_LIMIT_RPM)
            last_log = now

    log.info("Traversal complete: processed_nodes=%d created_edges=%d", processed, created_edges)

# --------------------
# Smoke
# --------------------

def smoke_test(sess):
    sess.run("CREATE (:SmokeTest {ts: timestamp()})")
    c = sess.run("MATCH (s:SmokeTest) RETURN count(s) AS c").single()["c"]
    sess.run("MATCH (s:SmokeTest) DELETE s")
    return c

# --------------------
# Main
# --------------------

def main():
    log.info("Connecting to %s db=%s user=%s", NEO4J_URI, NEO4J_DB, NEO4J_USER)
    release = resolve_release()
    global DATASET
    DATASET = f"SNOMEDCT:{SNOMED_BRANCH}:{release}"
    log.info("Dataset: %s | Root: %s | RPM limit: %d | FORCE=%s", DATASET, SNOMED_ROOT_ID, RATE_LIMIT_RPM, FORCE)

    # Confirm root exists + get its title for logging
    try:
        root = fetch_concept(SNOMED_ROOT_ID)
        title = extract_title(root) or "Clinical finding"
        log.info("Found SNOMED root: [%s] %s", SNOMED_ROOT_ID, title)
    except Exception as e:
        log.error("Failed to fetch root concept %s: %s", SNOMED_ROOT_ID, e)
        sys.exit(2)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session(database=NEO4J_DB, default_access_mode=WRITE_ACCESS) as sess:
            sc = smoke_test(sess)
            log.info("Smoke test wrote/seen %s temp node(s) (expected >==1)", sc)

            ensure_constraints(sess)

            if dataset_already_completed(sess) and not FORCE:
                log.info("Ingest already completed for dataset %s. Set FORCE=1 to rebuild.", DATASET)
                return

            if FORCE:
                delete_dataset(sess)

            run_uid = str(uuid.uuid4())
            start_ingest(sess, run_uid, SNOMED_ROOT_ID, release)
            c = sess.run("MATCH (i:Ingest {uid:$uid}) RETURN count(i) AS c", uid=run_uid).single()["c"]
            log.info("Ingest node created? count=%s", c)

            t0 = time.time()
            ingest_tree(sess, SNOMED_ROOT_ID)
            n, r = finish_ingest(sess, run_uid)
            dt = time.time() - t0
            log.info("DONE | dataset=%s uid=%s nodes=%d edges=%d elapsed=%.1fs", DATASET, run_uid, n, r, dt)
    finally:
        driver.close()

if __name__ == "__main__":
    main()

