#!/usr/bin/env python3

"""
DrugBank Discovery API -> Neo4j (flat tree with run markers & rate limiting)

- Synthetic root: "DrugBank" (root -> each drug)
- Label: :DRUG
- Relationship: :HAS_CHILD (parent -> drug)
- Node props: id, code, title, ds   (ds = dataset tag like "DrugBank:API:2025-10")
- Run marker: :Ingest {uid, dataset, release, startedAt, finishedAt, nodeCount, edgeCount}
  with (Ingest)-[:ROOT]->(Root node)
"""

import os
import sys
import time
import uuid
import logging
from datetime import datetime, timezone

import requests
from neo4j import GraphDatabase, WRITE_ACCESS
from dotenv import load_dotenv, find_dotenv

# --- Env ---

env_path = find_dotenv(usecwd=True)
if not env_path:
    print("ERROR: .env not found at repo root"); sys.exit(1)
load_dotenv(env_path)

DRUGBANK_API_BASE = os.getenv("DRUGBANK_API_BASE", "https://api.drugbank.com/discovery/v1")
DRUGBANK_API_KEY = os.getenv("DRUGBANK_API_KEY")
if not DRUGBANK_API_KEY:
    print("ERROR: Missing DRUGBANK_API_KEY in .env"); sys.exit(1)

DRUGBANK_RELEASE = os.getenv("DRUGBANK_RELEASE", "API")
ROOT_ID = os.getenv("DRUGBANK_ROOT_ID", "drugbank:root")
ROOT_TITLE = os.getenv("DRUGBANK_ROOT_TITLE", "DrugBank")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

FORCE = os.getenv("FORCE", "0") == "1"

RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "100"))
MIN_INTERVAL_S = 60.0 / max(1, RATE_LIMIT_RPM)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("drugbank_api_loader")

DATASET = f"DrugBank:{DRUGBANK_RELEASE}"

# --- Neo4j ---

CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT drug_node_id IF NOT EXISTS FOR (n:DRUG) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ingest_uid IF NOT EXISTS FOR (i:Ingest) REQUIRE i.uid IS UNIQUE",
]

UPSERT_NODE = """
MERGE (n:DRUG {id: $id})
  ON CREATE SET n.code = $code, n.title = $title, n.ds = $ds
  ON MATCH  SET n.code = coalesce(n.code, $code), n.title = coalesce(n.title, $title), n.ds = $ds
"""

UPSERT_EDGE = """
MATCH (p:DRUG {id: $parent})
MATCH (c:DRUG {id: $child})
MERGE (p)-[:HAS_CHILD]->(c)
"""

CREATE_INGEST_START = """
CREATE (i:Ingest { uid: $uid, dataset: $dataset, release: $release, startedAt: $startedAt })
RETURN i
"""

MARK_INGEST_DONE = """
MATCH (i:Ingest {uid: $uid})
SET i.finishedAt = $finishedAt, i.nodeCount = $nodeCount, i.edgeCount = $edgeCount
"""

LINK_INGEST_ROOT = """
MATCH (i:Ingest {uid: $uid})
MATCH (r:DRUG {id: $rootId})
MERGE (i)-[:ROOT]->(r)
"""

CHECK_ALREADY_DONE = """
MATCH (i:Ingest {dataset: $dataset}) WHERE i.finishedAt IS NOT NULL RETURN i LIMIT 1
"""

COUNT_NODES_EDGES_FOR_DATASET = """
MATCH (n:DRUG {ds: $ds}) WITH count(n) AS n
MATCH (:DRUG {ds: $ds})-[rel:HAS_CHILD]->(:DRUG {ds: $ds})
RETURN n, count(rel) AS r
"""

# --- API ---

class RateLimiter:
    def __init__(self, min_interval_s: float):
        self.min_interval = min_interval_s
        self.last_ts = 0.0
    def wait(self):
        now = time.monotonic(); delta = now - self.last_ts
        if delta < self.min_interval: time.sleep(self.min_interval - delta)
        self.last_ts = time.monotonic()

limiter = RateLimiter(MIN_INTERVAL_S)

def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def headers():
    return {"Authorization": DRUGBANK_API_KEY, "Accept": "application/json"}

def _respect_retry_after(r):
    ra = r.headers.get("Retry-After")
    if ra:
        try:
            secs = float(ra); log.warning("Retry-After: %.2fs", secs); time.sleep(secs); return
        except Exception:
            pass
    time.sleep(2.5)

def get_json(url: str, params=None, max_retries=6):
    attempt = 0
    while True:
        attempt += 1; limiter.wait()
        try:
            r = requests.get(url, headers=headers(), params=params or {}, timeout=60)
            if r.status_code == 429:
                log.warning("HTTP 429 on %s (attempt %d/%d)", url, attempt, max_retries)
                _respect_retry_after(r)
                if attempt < max_retries: continue
            r.raise_for_status(); return r
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            body = (e.response.text[:400] + "...") if getattr(e.response, "text", "") else ""
            log.warning("Request failed [%s] %s | status=%s | body=%.120s", url, e, status, body)
            if status in (429, 500, 502, 503, 504) and attempt < max_retries:
                _respect_retry_after(e.response if hasattr(e, "response") else r)
                continue
            raise

API_DRUGS = lambda: f"{DRUGBANK_API_BASE.rstrip('/')}/drugs"

def iter_drugs(per_page=100):
    page = 1
    while True:
        resp = get_json(API_DRUGS(), params={"per_page": per_page, "page": page})
        try:
            data = resp.json()
        except Exception:
            data = []
        items = data if isinstance(data, list) else (data.get("items") if isinstance(data, dict) else [])
        if not items: break
        for d in items:
            dbid = d.get("drugbank_id") or d.get("id")
            name = d.get("name") or d.get("generic_name") or d.get("brand_name") or ""
            if dbid: yield dbid, name
        link = resp.headers.get("Link", "")
        if link and 'rel="next"' in link:
            page += 1
        else:
            page += 1

# --- Neo4j helpers ---

def ensure_constraints(sess):
    for q in CREATE_CONSTRAINTS: sess.run(q)

def upsert_node(sess, code: str, title: str):
    sess.run(UPSERT_NODE, id=code, code=code, title=title or None, ds=DATASET)

def upsert_edge(sess, parent_id: str, child_id: str):
    sess.run(UPSERT_EDGE, parent=parent_id, child=child_id)

def dataset_already_completed(sess) -> bool:
    rec = sess.run(CHECK_ALREADY_DONE, dataset=DATASET).single(); return bool(rec)

def start_ingest(sess, uid: str, root_id: str, release: str):
    sess.run(CREATE_INGEST_START, uid=uid, dataset=DATASET, release=release, startedAt=utc_iso())
    sess.run(LINK_INGEST_ROOT, uid=uid, rootId=root_id)

def finish_ingest(sess, uid: str):
    rec = sess.run(COUNT_NODES_EDGES_FOR_DATASET, ds=DATASET).single()
    n = rec["n"] if rec and "n" in rec else 0
    r = rec["r"] if rec and "r" in rec else 0
    sess.run(MARK_INGEST_DONE, uid=uid, finishedAt=utc_iso(), nodeCount=n, edgeCount=r)
    return n, r

def delete_dataset(sess):
    log.warning("Deleting dataset %s…", DATASET)
    sess.run("MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i", ds=DATASET)
    sess.run("MATCH (n:DRUG {ds: $ds}) DETACH DELETE n", ds=DATASET)

# --- Ingest ---

def ingest_all(sess, root_id: str, root_title: str):
    upsert_node(sess, root_id, root_title)
    processed = 0; edges = 0; last_log = time.monotonic()
    for code, title in iter_drugs():
        upsert_node(sess, code, title); upsert_edge(sess, root_id, code)
        processed += 1; edges += 1
        now = time.monotonic()
        if now - last_log >= 2.0:
            log.info("Progress: nodes=%d edges=%d rpm=%d", processed + 1, edges, RATE_LIMIT_RPM)
            last_log = now
    log.info("Traversal complete: processed_nodes=%d created_edges=%d", processed + 1, edges)

# --- Smoke ---

def smoke_test(sess):
    sess.run("CREATE (:SmokeTest {ts: timestamp()})")
    c = sess.run("MATCH (s:SmokeTest) RETURN count(s) AS c").single()["c"]
    sess.run("MATCH (s:SmokeTest) DELETE s")
    return c

# --- Main ---

def main():
    log.info("Connecting to %s db=%s user=%s", NEO4J_URI, NEO4J_DB, NEO4J_USER)
    log.info("Dataset: %s | API: %s | FORCE=%s", DATASET, DRUGBANK_API_BASE, FORCE)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session(database=NEO4J_DB, default_access_mode=WRITE_ACCESS) as sess:
            sc = smoke_test(sess); log.info("Smoke test wrote/seen %s temp node(s) (expected >==1)", sc)
            ensure_constraints(sess)

            if dataset_already_completed(sess) and not FORCE:
                log.info("Ingest already completed for dataset %s. Set FORCE=1 to rebuild.", DATASET); return
            if FORCE: delete_dataset(sess)

            run_uid = str(uuid.uuid4())
            start_ingest(sess, run_uid, ROOT_ID, DRUGBANK_RELEASE)
            c = sess.run("MATCH (i:Ingest {uid:$uid}) RETURN count(i) AS c", uid=run_uid).single()["c"]
            log.info("Ingest node created? count=%s", c)

            t0 = time.time(); ingest_all(sess, ROOT_ID, ROOT_TITLE)
            n, r = finish_ingest(sess, run_uid); dt = time.time() - t0
            log.info("DONE | dataset=%s uid=%s nodes=%d edges=%d elapsed=%.1fs", DATASET, run_uid, n, r, dt)
    finally:
        driver.close()

if __name__ == "__main__":
    main()

