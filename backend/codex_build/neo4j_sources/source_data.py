#!/usr/bin/env python3

"""
Neo4j Singular Data Source
"""

import os
import sys
import time
import uuid
import re
import logging
from datetime import datetime, timezone
from collections import deque

import requests
from neo4j import GraphDatabase, WRITE_ACCESS
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")
NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

FORCE = os.getenv("FORCE", "0") == "1"

class SharedRateLimiter:
    def __init__(self, RATE_LIMIT_RPM: int):
        self.min_interval = 60.0 / max(1, RATE_LIMIT_RPM)
        self.last_ts = 0.0
    def wait(self):
        now = time.monotonic()
        delta = now - self.last_ts
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self.last_ts = time.monotonic()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("global_root_loader")

def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _respect_retry_after(r):
    ra = r.headers.get("Retry-After") if hasattr(r, "headers") else None
    if ra:
        try:
            secs = float(ra)
            log.warning("Retry-After: sleeping %.2fs", secs)
            time.sleep(secs)
            return
        except Exception:
            pass
    time.sleep(2.5)

def smoke_test(sess):
    sess.run("CREATE (:SmokeTest {ts: timestamp()})")
    c = sess.run("MATCH (s:SmokeTest) RETURN count(s) AS c").single()["c"]
    sess.run("MATCH (s:SmokeTest) DELETE s")
    return c

# Separate by \
def conceptID(text: str, symptom: str = None, source: str = None) -> str:
    if not text:
        return "unknown"
    text = text.lower().strip()
    text = text.replace(',', '-')
    text = re.sub(r'[^a-z0-9,-]', '', text)
    text = re.sub(r'-+', '-', text)

    clean_symptom = ""
    if symptom:
        clean_symptom = re.sub(r'[^a-z0-9-]', '', source.lower().strip())
    text = f"{text}-{clean_symptom}"

    clean_source = ""
    if source:
        clean_source = re.sub(r'[^a-z0-9-]', '', source.lower().strip())
    text = f"{text}-{clean_source}"
        
    return text


# --------------------
# DrugBank
# --------------------

def drugbank(driver):
    DRUGBANK_API_BASE = os.getenv("DRUGBANK_API_BASE", "https://api.drugbank.com/discovery/v1")
    DRUGBANK_API_KEY = os.getenv("DRUGBANK_API_KEY")
    if not DRUGBANK_API_KEY:
        print("ERROR: Missing DRUGBANK_API_KEY in .env"); return

    DRUGBANK_RELEASE = os.getenv("DRUGBANK_RELEASE", "API")
    ROOT_ID = os.getenv("DRUGBANK_ROOT_ID", "drugbank:root")
    ROOT_TITLE = os.getenv("DRUGBANK_ROOT_TITLE", "DrugBank")
    DATASET = f"DrugBank:{DRUGBANK_RELEASE}"

    limiter = SharedRateLimiter(int(os.getenv("RATE_LIMIT_RPM", "100")))

    def drugbank_headers():
        return {"Authorization": DRUGBANK_API_KEY, "Accept": "application/json"}

    def get_json(url: str, params=None, max_retries=6):
        attempt = 0
        while True:
            attempt += 1; limiter.wait()
            try:
                r = requests.get(url, headers=drugbank_headers(), params=params or {}, timeout=60)
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
                if dbid: yield d, dbid, name
            link = resp.headers.get("Link", "")
            if link and 'rel="next"' in link:
                page += 1
            else:
                page += 1

    with driver.session(database=NEO4J_DB, default_access_mode=WRITE_ACCESS) as sess:
        sess.run("CREATE CONSTRAINT drug_node_id IF NOT EXISTS FOR (n:DRUG) REQUIRE n.id IS UNIQUE")
        sess.run("CREATE CONSTRAINT ingest_uid IF NOT EXISTS FOR (i:Ingest) REQUIRE i.uid IS UNIQUE")

        if bool(sess.run("MATCH (i:Ingest {dataset: $ds}) WHERE i.finishedAt IS NOT NULL RETURN i LIMIT 1", ds=DATASET).single()) and not FORCE:
            log.info("DrugBank Ingest already completed. Skipping.")
            return
        
        if FORCE: 
            sess.run("MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i", ds=DATASET)
            sess.run("MATCH (n:DRUG {ds: $ds}) DETACH DELETE n", ds=DATASET)

        run_uid = str(uuid.uuid4())
        sess.run("CREATE (i:Ingest { uid: $uid, dataset: $ds, release: $release, startedAt: $startedAt })", uid=run_uid, ds=DATASET, release=DRUGBANK_RELEASE, startedAt=utc_iso())
        sess.run("MERGE (n:DRUG {id: $id}) ON CREATE SET n.code = $id, n.title = $title, n.ds = $ds", id=ROOT_ID, title=ROOT_TITLE, ds=DATASET)
        sess.run("MATCH (i:Ingest {uid: $uid}), (r:DRUG {id: $rootId}) MERGE (i)-[:ROOT]->(r)", uid=run_uid, rootId=ROOT_ID)

        for d, code, title in iter_drugs():
            symptoms = d.get("symptoms", [])
            for symptom_name in symptoms:
                if not symptom_name:
                    continue
                concept_id = concept_id(title, symptom_name, source="drugbank")

                sess.run("MERGE (n:DRUG {id: $id}) ON CREATE SET n.conceptID=$conceptID, n.code=$id, n.title=$t, n.ds=$ds ON MATCH SET n.ds=$ds", id=code, conceptID=concept_id, t=title or None, ds=DATASET)
                sess.run("MATCH (p:DRUG {id: $parent}), (c:DRUG {id: $child}) MERGE (p)-[:HAS_CHILD]->(c)", parent=ROOT_ID, child=code)

        rec = sess.run("MATCH (n:DRUG {ds: $ds}) WITH count(n) AS n MATCH (:DRUG {ds: $ds})-[rel:HAS_CHILD]->(:DRUG {ds: $ds}) RETURN n, count(rel) AS r", ds=DATASET).single()
        sess.run("MATCH (i:Ingest {uid: $uid}) SET i.finishedAt = $finishedAt, i.nodeCount = $nodeCount, i.edgeCount = $edgeCount", uid=run_uid, finishedAt=utc_iso(), nodeCount=rec["n"], edgeCount=rec["r"])

# --------------------
# SNOMED
# --------------------

def snomed(driver):
    SNOWSTORM_BASE = os.getenv("SNOWSTORM_BASE", "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct")
    SNOMED_BRANCH = os.getenv("SNOMED_BRANCH", "MAIN")
    SNOMED_ROOT_ID = os.getenv("SNOMED_ROOT_ID", "404684003")
    SNOMED_RELEASE = os.getenv("SNOMED_RELEASE", "")
    
    limiter = SharedRateLimiter(int(os.getenv("RATE_LIMIT_RPM", "200")))

    def api_get(path, params=None):
        limiter.wait()
        r = requests.get(f"{SNOWSTORM_BASE.rstrip('/')}/{path.lstrip('/')}", headers={"Accept": "application/json", "Accept-Language": os.getenv("ACCEPT_LANGUAGE", "en"), "User_Agent": "logan.watersmith@grey-box.ca"}, params=params or {}, timeout=60)
        r.raise_for_status()
        return r.json()

    release = SNOMED_RELEASE or "latest"
    try:
        v_data = api_get("codesystems/SNOMEDCT/versions")
        items = v_data.get("items") if isinstance(v_data, dict) else v_data
        if items: release = items[0].get("version") or items[0].get("effectiveDate") or "latest"
    except Exception: pass

    DATASET = f"SNOMEDCT:{SNOMED_BRANCH}:{release}"

    with driver.session(database=NEO4J_DB, default_access_mode=WRITE_ACCESS) as sess:
        sess.run("CREATE CONSTRAINT snomed_node_id IF NOT EXISTS FOR (n:SNOMED) REQUIRE n.id IS UNIQUE")
        if bool(sess.run("MATCH (i:Ingest {dataset: $ds}) WHERE i.finishedAt IS NOT NULL RETURN i LIMIT 1", ds=DATASET).single()) and not FORCE:
            log.info("SNOMED CT Ingest already completed. Skipping."); return
        
        if FORCE:
            sess.run("MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i", ds=DATASET)
            sess.run("MATCH (n:SNOMED {ds: $ds}) DETACH DELETE n", ds=DATASET)

        run_uid = str(uuid.uuid4())
        sess.run("CREATE (i:Ingest {uid:$uid, dataset:$ds, release:$rel, startedAt:$s})", uid=run_uid, ds=DATASET, rel=release, s=utc_iso())

        def upsert_snomed_node(node):
            cid = node.get("conceptId") or node.get("id") or ""
            if not cid: return None
            term = node.get("pt", {}).get("term") or node.get("fsn", {}).get("term") or node.get("term", "")
            sess.run("MERGE (n:SNOMED {id: $id}) ON CREATE SET n.code=$id, n.title=$t, n.ds=$ds ON MATCH SET n.ds=$ds", id=cid, t=term or None, ds=DATASET)
            return cid

        root_full = None
        retries = 3
        
        for attempt in range(retries):
            try:
                log.info("Fetching SNOMED root concept %s (Attempt %d/%d)...", SNOMED_ROOT_ID, attempt + 1, retries)
                root_full = api_get(f"browser/{SNOMED_BRANCH}/concepts/{SNOMED_ROOT_ID}")
                break  # Success! Break out of the retry loop
            except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.exceptions.RequestException) as net_err:
                log.warning("SNOMED Server dropped connection on root lookup: %s", net_err)
                if attempt < retries - 1:
                    log.info("Sleeping 5s before retrying root lookup...")
                    time.sleep(5.0)
                else:
                    log.error("Failed all retries to connect to SNOMED server. Skipping SNOMED module completely.")
                    return  # Safely exits run_snomed() so main() moves to RxNorm

        # If it passed but root_full is somehow empty, exit gracefully
        if not root_full:
            return

        # Core initialization with the database
        upsert_snomed_node(root_full)
        sess.run("MATCH (i:Ingest {uid: $uid}), (r:SNOMED {id: $rid}) MERGE (i)-[:ROOT]->(r)", uid=run_uid, rid=SNOMED_ROOT_ID)

        # BFS Tree Traversal
        queue = deque([(SNOMED_ROOT_ID, None)])
        visited = set()

        while queue:
            cid, parent = queue.popleft()
            if cid in visited: continue
            visited.add(cid)

            try:
                full = api_get(f"browser/{SNOMED_BRANCH}/concepts/{cid}")
                upsert_snomed_node(full)
                if parent:
                    sess.run("MATCH (p:SNOMED {id: $p}), (c:SNOMED {id: $c}) MERGE (p)-[:HAS_CHILD]->(c)", p=parent, c=cid)
                
                children = api_get(f"browser/{SNOMED_BRANCH}/concepts/{cid}/children")
                items = children if isinstance(children, list) else children.get("items", [])
                for ch in items:
                    ch_id = ch.get("conceptId") or ch.get("id")
                    if ch_id and ch_id not in visited: queue.append((ch_id, cid))
            except Exception as e:
                log.warning("Failed step processing SNOMED code %s: %s", cid, e)

        rec = sess.run("MATCH (n:SNOMED {ds: $ds}) WITH count(n) AS n MATCH (:SNOMED {ds: $ds})-[rel:HAS_CHILD]->(:SNOMED {ds: $ds}) RETURN n, count(rel) AS r", ds=DATASET).single()
        sess.run("MATCH (i:Ingest {uid: $uid}) SET i.finishedAt=$f, i.nodeCount=$n, i.edgeCount=$r", uid=run_uid, f=utc_iso(), n=rec["n"], r=rec["r"])

# --------------------
# RXNORM
# --------------------

def rxnorm(driver):
    PRESCRIBABLE_ONLY = os.getenv("RXN_PRESCRIBABLE", "1") == "1"
    RXN_RELEASE_ID = os.getenv("RXN_RELEASE_ID", "current")
    DATASET = f"RxNorm:{'prescribable' if PRESCRIBABLE_ONLY else 'all'}:{RXN_RELEASE_ID}"
    FORCE_RX = os.getenv("RXFORCE", "0") == "1" or FORCE

    limiter = SharedRateLimiter(int(os.getenv("RATE_LIMIT_RPM", "120")))
    ROOT_TTYS = [t.strip() for t in os.getenv("RXN_ROOT_TTYS", "IN,MIN,PIN").split(",") if t.strip()]
    CHILD_TTYS = [t.strip() for t in os.getenv("RXN_CHILD_TTYS", "SCD,SBD,GPCK,BPCK,SCDF,SBDF,SCDC,SBDC,BN").split(",") if t.strip()]

    def rx_get(path, params=None):
        limiter.wait()
        prefix = "/Prescribe" if PRESCRIBABLE_ONLY else ""
        r = requests.get(f"https://rxnav.nlm.nih.gov/REST{prefix}{path}", params=params or {}, timeout=60)
        r.raise_for_status()
        return r.json()

    with driver.session(database=NEO4J_DB) as sess:
        sess.run("CREATE CONSTRAINT rxn_node_rxcui IF NOT EXISTS FOR (n:RXN) REQUIRE n.rxcui IS UNIQUE")
        if bool(sess.run("MATCH (i:Ingest {dataset: $ds}) WHERE i.finishedAt IS NOT NULL RETURN i LIMIT 1", ds=DATASET).single()) and not FORCE_RX:
            log.info("RxNorm Ingest already completed. Skipping."); return

        if FORCE_RX:
            sess.run("MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i", ds=DATASET)
            sess.run("MATCH (n:RXN {ds: $ds}) DETACH DELETE n", ds=DATASET)

        run_uid = str(uuid.uuid4())
        sess.run("CREATE (i:Ingest {uid:$uid, dataset:$ds, release:$rel, startedAt:$s})", uid=run_uid, ds=DATASET, rel=RXN_RELEASE_ID, s=utc_iso())
        sess.run("MERGE (n:RXN {rxcui: 'ROOT'}) ON CREATE SET n.name='RxNorm', n.tty='ROOT', n.ds=$ds", ds=DATASET)
        sess.run("MATCH (i:Ingest {uid: $uid}), (r:RXN {rxcui: 'ROOT'}) MERGE (i)-[:ROOT]->(r)", uid=run_uid)

        # Get top-level concepts
        js = rx_get("/allconcepts.json", params={"tty": " ".join(ROOT_TTYS)})
        roots = [{"rxcui": m.get("rxcui"), "name": m.get("name"), "tty": m.get("tty")} for m in js.get("minConceptGroup", {}).get("minConcept", []) if m.get("rxcui")]

        for m in roots:
            concept_id = conceptID(m.get("name"), source="rxnorm")
            sess.run("MERGE (n:RXN {rxcui: $rxcui}) ON CREATE SET n.conceptID=$conceptID, n.name=$name, n.tty=$tty, n.ds=$ds", rxcui=m["rxcui"], conceptID=concept_id, name=m["name"], tty=m["tty"], ds=DATASET)
            sess.run("MATCH (p:RXN {rxcui: 'ROOT'}), (c:RXN {rxcui: $c}) MERGE (p)-[:HAS_CHILD]->(c)", c=m["rxcui"])

        for idx, m in enumerate(roots):
            if idx % 250 == 0: log.info("RxNorm build processing roots: %d / %d", idx, len(roots))
            try:
                rel_js = rx_get(f"/rxcui/{m['rxcui']}/allrelated.json")
                groups = rel_js.get("allRelatedGroup", {}).get("conceptGroup", [])
                for g in groups:
                    tty = g.get("tty")
                    if tty not in CHILD_TTYS: continue
                    props = g.get("conceptProperties", [])
                    if isinstance(props, dict): props = [props]
                    for p in props:
                        if p.get("rxcui"):
                            concept_id = conceptID(p.get("name"), source="rxnorm")
                            sess.run("MERGE (n:RXN {rxcui: $rxcui}) ON CREATE SET n.conceptID=$conceptID, n.name=$name, n.tty=$tty, n.ds=$ds ON MATCH SET n.ds=$ds", rxcui=p["rxcui"], conceptID=concept_id, name=p["name"], tty=p["tty"], ds=DATASET)
                            sess.run("MATCH (p:RXN {rxcui: $p}), (c:RXN {rxcui: $c}) MERGE (p)-[:HAS_CHILD]->(c)", p=m["rxcui"], c=p["rxcui"])
            except Exception as e: log.debug("Skipped paths on CUI %s: %s", m["rxcui"], e)

        rec = sess.run("MATCH (n:RXN {ds: $ds}) WITH count(n) AS n MATCH (:RXN {ds: $ds})-[rel:HAS_CHILD]->(:RXN {ds: $ds}) RETURN n, count(rel) AS r", ds=DATASET).single()
        sess.run("MATCH (i:Ingest {uid: $uid}) SET i.finishedAt=$f, i.nodeCount=$n, i.edgeCount=$r", uid=run_uid, f=utc_iso(), n=rec["n"], r=rec["r"])

# --------------------
# ICD-11
# --------------------

def icd11(driver):
    ICD_CLIENT_ID = os.getenv("ICD_CLIENT_ID")
    ICD_CLIENT_SECRET = os.getenv("ICD_CLIENT_SECRET")
    if not ICD_CLIENT_ID or not ICD_CLIENT_SECRET:
        log.error("Missing ICD credentials. Skipping ICD-11."); return

    ICD_RELEASE_ID = os.getenv("ICD_RELEASE_ID", "2024-01")
    DATASET = f"ICD11-21:{ICD_RELEASE_ID}"
    limiter = SharedRateLimiter(int(os.getenv("RATE_LIMIT_RPM", "200")))

    limiter.wait()
    tok_r = requests.post("https://icdaccessmanagement.who.int/connect/token", data={"grant_type": "client_credentials", "scope": "icdapi_access"}, auth=(ICD_CLIENT_ID, ICD_CLIENT_SECRET), timeout=30)
    tok_r.raise_for_status()
    token = tok_r.json()["access_token"]

    def icd_get(url, params=None, max_retries=6):
        attempt = 0
        while True:
            attempt += 1; limiter.wait()
            try:
                r = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "API-Version": "v2", "Accept-Language": "en"}, params=params or {}, timeout=60)
                if r.status_code == 429:
                    _respect_retry_after(r); 
                    if attempt < max_retries: 
                        continue
                r.raise_for_status(); return r.json()
            except requests.HTTPError as e:
                if getattr(e.response, "status_code", None) in (429, 500, 502, 503, 504) and attempt < max_retries:
                    _respect_retry_after(e.response); continue
                raise

    def get_node_details(item):
        if isinstance(item, str):
            res = icd_get(item, params={"properties": "code,title"})
            t = res.get("title", "")
            return item, res.get("code") or res.get("theCode") or "", t.get("@value", "") if isinstance(t, dict) else t
        return item.get("@id"), item.get("code") or item.get("theCode") or "", item.get("title", {}).get("@value", "") if isinstance(item.get("title"), dict) else item.get("title", "")

    # Look up Chapter 21 Root
    root_res = icd_get(f"https://id.who.int/icd/release/11/{ICD_RELEASE_ID}/mms", params={"flat": "true"})
    ch21_id = None
    for child in root_res.get("child", []):
        nid, code, title = get_node_details(child)
        if code == "21" or "Symptoms, signs" in str(title): ch21_id = nid; break

    if not ch21_id: log.error("Could not find ICD-11 Chapter 21 node. Skipping."); return

    with driver.session(database=NEO4J_DB) as sess:
        sess.run("CREATE CONSTRAINT icd_node_id IF NOT EXISTS FOR (n:ICD) REQUIRE n.id IS UNIQUE")
        if bool(sess.run("MATCH (i:Ingest {dataset: $ds}) WHERE i.finishedAt IS NOT NULL RETURN i LIMIT 1", ds=DATASET).single()) and not FORCE:
            log.info("ICD-11 Ingest already completed. Skipping."); return

        if FORCE:
            sess.run("MATCH (i:Ingest {dataset: $ds}) DETACH DELETE i", ds=DATASET)
            sess.run("MATCH (n:ICD {ds: $ds}) DETACH DELETE n", ds=DATASET)

        run_uid = str(uuid.uuid4())
        sess.run("CREATE (i:Ingest {uid:$uid, dataset:$ds, release:$rel, startedAt:$s})", uid=run_uid, ds=DATASET, rel=ICD_RELEASE_ID, s=utc_iso())
        
        full_root = icd_get(ch21_id)
        # sess.run("MERGE (n:ICD {id: $id}) ON CREATE SET n.code=$c, n.title=$t, n.ds=$ds", id=ch21_id, c=full_root.get("code"), t=full_root.get("title", {}).get("@value"), ds=DATASET)
        sess.run("MERGE (n:ICD {id: $id}) ON CREATE SET n.code=$c, n.title='ICD 11', n.ds=$ds", id=ch21_id, c=full_root.get("code"), ds=DATASET)        
        sess.run("MATCH (i:Ingest {uid: $uid}), (r:ICD {id: $rid}) MERGE (i)-[:ROOT]->(r)", uid=run_uid, rid=ch21_id)

        queue = deque([(ch21_id, None)])
        visited = set()
        while queue:
            nid, parent = queue.popleft()
            if nid in visited: continue
            visited.add(nid)

            full = icd_get(nid)
            t_val = full.get("title", {})
            title_str = t_val.get("@value") if isinstance(t_val, dict) else t_val
            sess.run("MERGE (n:ICD {id: $id}) ON CREATE SET n.code=$c, n.title=$t, n.ds=$ds ON MATCH SET n.ds=$ds", id=nid, c=full.get("code") or full.get("theCode"), t=title_str, ds=DATASET)
            if parent:
                sess.run("MATCH (p:ICD {id: $p}), (c:ICD {id: $c}) MERGE (p)-[:HAS_CHILD]->(c)", p=parent, c=nid)

            subtree = icd_get(nid, params={"include": "descendant", "depth": "1", "properties": "code,title"})
            children = subtree.get("child", []) or subtree.get("descendant", [])
            for child in children:
                cid, _, _ = get_node_details(child)
                if cid and cid not in visited: queue.append((cid, nid))

        rec = sess.run("MATCH (n:ICD {ds: $ds}) WITH count(n) AS n MATCH (:ICD {ds: $ds})-[rel:HAS_CHILD]->(:ICD {ds: $ds}) RETURN n, count(rel) AS r", ds=DATASET).single()
        sess.run("MATCH (i:Ingest {uid: $uid}) SET i.finishedAt=$f, i.nodeCount=$n, i.edgeCount=$r", uid=run_uid, f=utc_iso(), n=rec["n"], r=rec["r"])

# --------------------
# Combining into Singular Data Source
# --------------------

def unify_graph(driver):
    log.info(">>> Combining graphes into a singular source...")
    
    with driver.session(database=NEO4J_DB) as sess:
        sess.run("""
                MERGE (g:G_ROOT {id: 'GLOBAL_ROOT'})
                ON CREATE SET g.title = 'Global Root', g.initializedAt = $ts
            """, ts=utc_iso())
        
        # Secondary label (:Concept) applied to every medical node
        log.info("Creating global structural indexes...")
        sess.run("CREATE INDEX global_concept_code IF NOT EXISTS FOR (n:Concept) ON n.code")

        sess.run("""
            MATCH (:Ingest)-[:ROOT]->(root)
            SET root:Source
        """)
        
        log.info("Applying global :Concept labels to all internal medical entities...")
        sess.run("MATCH (n:DRUG) WHERE NOT n:Source SET n:Concept")
        sess.run("MATCH (n:SNOMED) WHERE NOT n:Source SET n:Concept")
        sess.run("MATCH (n:RXN) WHERE NOT n:Source SET n:Concept")
        sess.run("MATCH (n:ICD) WHERE NOT n:Source SET n:Concept")
        
        log.info("Creating connections between RxNorm and DrugBank...")
        sess.run("""
            MATCH (r:RXN:Concept), (d:DRUG:Concept)
            WHERE r.name = d.title OR r.rxcui = d.code
            MERGE (r)-[:SAME_AS {derivedBy: 'property_match'}]->(d)
        """)
        
        log.info("Creating connections between SNOMED CT and ICD-11...")
        sess.run("""
            MATCH (s:SNOMED:Concept), (i:ICD:Concept)
            WHERE s.code = i.code OR s.title = i.title
            MERGE (s)-[:MAPS_TO {derivedBy: 'exact_string_match'}]->(i)
        """)

        sess.run("""
                MATCH (g:G_ROOT {id: 'GLOBAL_ROOT'}), (src:Source)
                MERGE (g)-[:HAS_SOURCE]->(src)
            """)
        
    log.info("<<< Graph combination complete. All sources are now connected.")

def print_databases(driver):
    # Create .txt file
    with open("databases.txt", "w") as file:
        file.write("\n" + "="*60 + "\nIMPORTED DATABASES\n" + "="*60 + "\n")
        vocab_labels = ["DRUG", "SNOMED", "RXN", "ICD"]
        
        with driver.session(database=NEO4J_DB) as sess:
            for label in vocab_labels:
                query = f"""
                    MATCH (n:{label})
                    RETURN n.id AS node_id, properties(n) AS all_fields
                """
                results = sess.run(query)

                if label == "DRUG":
                    log.info("Importing DrugBank")
                    file.write(f"--- Database Records for DrugBank ---\n")
                if label == "SNOMED":
                    log.info("Importing SNOMED")
                    file.write(f"--- Database Records for Snomed ---\n")
                if label == "RXN":
                    log.info("Importing RxNorm")
                    file.write(f"--- Database Records for RxNorm ---\n")
                if label == "ICD":
                    log.info("Importing ICD 11")
                    file.write(f"--- Database Records for ICD 11 ---\n")
                
                has_records = False
                for record in results:
                    has_records = True
                    node_id = record["node_id"]
                    fields = record["all_fields"]
                    
                    formatted_fields = ", ".join([f"{k}: '{v}'" for k, v in fields.items()])
                    file.write(f"ID: [{node_id}] -> {{ {formatted_fields} }}\n")
                    
                if not has_records:
                    file.write(f"No records found for label :{label} (Skipped or Empty).\n")
                
        file.write("="*60 + "\nEND OF DATABASE READOUT\n" + "="*60)

def source_data(sources):
    log.info("=" * 60)
    log.info("Creating Singular Medical Knowledge Graph")
    log.info("=" * 60)
    
    t0 = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session(database=NEO4J_DB) as check_session:
            sc = smoke_test(check_session)
            log.info("Graph connection smoke test passed.")

        # Ingest separate sources into the single database based on user choice
        if "drugbank" in sources:
            log.info("Ingesting DrugBank.")
            drugbank(driver)
        if "snomed" in sources:
            log.info("Ingesting SNOMED.")
            snomed(driver)
        if "rxnorm" in sources:
            log.info("Ingesting RXNorm.")
            rxnorm(driver)
        if "icd11" in sources:
            log.info("Ingesting ICD11.")
            icd11(driver)

        # Link them together to make a singular source
        unify_graph(driver)

        print_databases(driver)

    except Exception as e:
        log.critical("Pipeline was terminated prematurely: %s", e)
        sys.exit(2)
    finally:
        driver.close()

    log.info("=" * 60)
    log.info("All pipelines executed | Total duration: %.2f seconds", time.time() - t0)
    log.info("=" * 60)

if __name__ == "__main__":
    sources = sys.argv[1:]
    source_data(sources)