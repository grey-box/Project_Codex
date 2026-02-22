#!/usr/bin/env python3

"""
- Root node: "RxNorm"
- Children under the root: Ingredients (IN, MIN, PIN) from RxNav (and/or optional Prescribable subset see config)
- From each ingredient attach via default RxNav paths
  SCD, SBD, GPCK, BPCK, SCDF, SBDF, SCDC, SBDC, BN, ...
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
from neo4j import GraphDatabase
from dotenv import load_dotenv, find_dotenv

# Config
# List of RX specific .env vars: RXN_PRESCRIBABLE, RXN_RELEASE_ID, RATE_LIMIT_RPM, RXN_ROOT_TTYS, RXFORCE 

env_path = find_dotenv(usecwd=True)
if not env_path:
    print("ERROR: .env not found at repo root")
    sys.exit(1)
load_dotenv(env_path)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

# Use Prescribable subset (smaller)
PRESCRIBABLE_ONLY = os.getenv("RXN_PRESCRIBABLE", "1") == "1"

RXN_RELEASE_ID = os.getenv("RXN_RELEASE_ID", "current")
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "120"))
MIN_INTERVAL_S = 60.0 / max(1, RATE_LIMIT_RPM)

# Logger
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("rxnorm_loader")

DATASET = f"RxNorm:{'prescribable' if PRESCRIBABLE_ONLY else 'all'}:{RXN_RELEASE_ID}"

ROOT_TTYS = [t.strip() for t in os.getenv("RXN_ROOT_TTYS", "IN,MIN,PIN").split(",") if t.strip()]
CHILD_TTYS = [t.strip() for t in os.getenv(
    "RXN_CHILD_TTYS",
    "SCD,SBD,GPCK,BPCK,SCDF,SBDF,SCDC,SBDC,BN"
).split(",") if t.strip()]

# API Handler

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"

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


def get_json(url: str, params=None, max_retries=6):
    attempt = 0
    while True:
        attempt += 1
        limiter.wait()
        try:
            r = requests.get(url, params=params or {}, timeout=60)
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                sleep_s = float(retry_after) if retry_after else 2.5
                log.warning("HTTP 429 on %s (attempt %d/%d) -> sleeping %.1fs", url, attempt, max_retries, sleep_s)
                time.sleep(sleep_s)
                if attempt < max_retries:
                    continue
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            body = (e.response.text[:500] + "...") if getattr(e.response, "text", "") else ""
            log.warning("Request failed [%s] %s | status=%s | body=%.120s", url, e, status, body)
            if status in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(2.5)
                continue
            raise


def rxnav_all_concepts_by_tty(ttys):
    tty_param = " ".join(ttys)  # RxNav expects space-separated TTY list (Keep in mind otherwise you'll go through a lot of pain)
    path = f"/Prescribe/allconcepts.json" if PRESCRIBABLE_ONLY else "/allconcepts.json"
    url = RXNAV_BASE + path
    js = get_json(url, params={"tty": tty_param})
    group = js.get("minConceptGroup", {})
    arr = group.get("minConcept") or []
    out = []
    for m in arr:
        rx = m.get("rxcui")
        nm = m.get("name")
        tty = m.get("tty")
        if rx and nm and tty:
            out.append({"rxcui": rx, "name": nm, "tty": tty})
    return out


def rxnav_all_related(rxcui: str):
    """
    Default-path related concepts grouped by tty for a given RXCUI.
    /REST/rxcui/{rxcui}/allrelated.json
    """
    url = f"{RXNAV_BASE}{'/Prescribe' if PRESCRIBABLE_ONLY else ''}/rxcui/{rxcui}/allrelated.json"
    js = get_json(url)
    groups = (js.get("allRelatedGroup") or {}).get("conceptGroup") or []
    result = {}
    for g in groups:
        tty = g.get("tty")
        props = g.get("conceptProperties") or []
        if not tty or not props:
            continue
        if isinstance(props, dict):  # sometimes its just a single object
            props = [props]
        result[tty] = [
            {
                "rxcui": p.get("rxcui"),
                "name": p.get("name"),
                "tty": p.get("tty"),
            }
            for p in props
            if p.get("rxcui") and p.get("name")
        ]
    return result

# Simple Neo4j schema (will be changed in the future)

CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT rxn_node_rxcui IF NOT EXISTS FOR (n:RXN) REQUIRE n.rxcui IS UNIQUE",
    "CREATE CONSTRAINT ingest_uid IF NOT EXISTS FOR (i:Ingest) REQUIRE i.uid IS UNIQUE",
]

UPSERT_NODE = """
MERGE (n:RXN {rxcui: $rxcui})
  ON CREATE SET n.name = $name, n.tty = $tty, n.ds = $ds
  ON MATCH  SET n.name = coalesce(n.name, $name),
              n.tty  = coalesce(n.tty,  $tty),
              n.ds   = $ds
"""

UPSERT_EDGE = """
MATCH (p:RXN {rxcui: $parent})
MATCH (c:RXN {rxcui: $child})
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
MATCH (r:RXN {rxcui: $rootId})
MERGE (i)-[:ROOT]->(r)
"""

CHECK_ALREADY_DONE = """
MATCH (i:Ingest {dataset: $dataset})
WHERE i.finishedAt IS NOT NULL
RETURN i LIMIT 1
"""

COUNT_NODES_EDGES_FOR_DATASET = """
MATCH (n:RXN {ds: $ds})
WITH count(n) AS n
MATCH (:RXN {ds: $ds})-[rel:HAS_CHILD]->(:RXN {ds: $ds})
RETURN n, count(rel) AS r
"""

# for FORCE=1 (RXFORCE in .env config) rebuilds (same syntax as ICD-11 script)
DELETE_DATASET_ALL = """
MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i;
MATCH (n:RXN {ds: $ds}) DETACH DELETE n;
"""

# Neo4j Functions

def ensure_constraints(sess):
    for q in CREATE_CONSTRAINTS:
        sess.run(q)


def upsert_node(sess, rxcui: str, name: str, tty: str | None):
    sess.run(UPSERT_NODE, rxcui=rxcui, name=name, tty=tty, ds=DATASET)


def upsert_edge(sess, parent: str, child: str):
    sess.run(UPSERT_EDGE, parent=parent, child=child)


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


# Ingest Data

def build_graph(sess):
    upsert_node(sess, "ROOT", "RxNorm", "ROOT")

    roots = rxnav_all_concepts_by_tty(ROOT_TTYS)
    log.info("Fetched %d root concepts for TTYs=%s", len(roots), ROOT_TTYS)

    for m in roots:
        upsert_node(sess, m["rxcui"], m["name"], m["tty"])
        upsert_edge(sess, "ROOT", m["rxcui"])

    processed = 0
    edges_created = 0
    for m in roots:
        processed += 1
        if processed % 250 == 0:
            log.info("Progress: roots processed=%d / %d", processed, len(roots))
        related = rxnav_all_related(m["rxcui"])  # grouped by tty
        for tty in CHILD_TTYS:
            for p in related.get(tty, []):
                upsert_node(sess, p["rxcui"], p["name"], p.get("tty"))
                upsert_edge(sess, m["rxcui"], p["rxcui"])
                edges_created += 1

    log.info("Child fan-out complete: processed=%d edges_created=%d", processed, edges_created)


def main():
    FORCE = os.getenv("RXFORCE", "0") == "1"

    log.info("Connecting to %s db=%s user=%s", NEO4J_URI, NEO4J_DB, NEO4J_USER)
    log.info("Dataset: %s | Prescribable=%s | RPM limit: %d | FORCE=%s",
             DATASET, PRESCRIBABLE_ONLY, RATE_LIMIT_RPM, FORCE)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session(database=NEO4J_DB) as sess:
            ensure_constraints(sess)

            if FORCE:
                log.warning("Deleting dataset %s before rebuild…", DATASET)
                sess.run(DELETE_DATASET_ALL, ds=DATASET)

            if dataset_already_completed(sess) and not FORCE:
                log.info("Ingest already completed for dataset %s. Set FORCE=1 to rebuild.", DATASET)
                return

            run_uid = str(uuid.uuid4())
            start_ingest(sess, run_uid, "ROOT", RXN_RELEASE_ID)
            start = time.time()

            build_graph(sess)

            n, r = finish_ingest(sess, run_uid)
            dt = time.time() - start
            log.info("DONE | dataset=%s uid=%s nodes=%d edges=%d elapsed=%.1fs",
                     DATASET, run_uid, n, r, dt)

    finally:
        driver.close()


if __name__ == "__main__":
    main()

