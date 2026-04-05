"""
Project Codex — RxNorm Source Loader
Reads sample_data/rxnorm_sample.json and maps into normalized Codex schema.
RxNorm is US-centric; creates EQUIVALENT_TO links to DrugBank nodes.
"""

import json
import requests
from datetime import datetime, timezone

# Map RxCUI → DrugBank ID for equivalence linking
RXCUI_TO_DRUGBANK = {
    "161":   "DB00316",   # Acetaminophen
    "1191":  "DB00945",   # Aspirin
    "6809":  "DB00331",   # Metformin
    "11289": "DB00682",   # Warfarin
    "7052":  "DB00563",   # Methotrexate
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def fetch_single_rxnorm(drug):
    r = requests.get(f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug}")
    data = r.json()
    rxids = data.get("idGroup", {}).get("rxnormId", [])

    if not rxids:
        return None

    rxcui = rxids[0]

    r2 = requests.get(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allrelated.json")
    related_data = r2.json()

    related_concepts = []
    for group in related_data.get("allRelatedGroup", {}).get("conceptGroup", []):
        tty = group.get("tty")
        for c in group.get("conceptProperties", []):
            related_concepts.append({
                "name": c["name"],
                "tty": tty
            })

    return {
        "rxcui": rxcui,
        "name": drug,
        "related_concepts": related_concepts
    }

def fetch_rxnorm_concepts(drug_names):
    concepts = []
    for d in drug_names:
        c = fetch_single_rxnorm(d)
        if c:
            concepts.append(c)
    return concepts

def insert_rxnorm_concept(db, concept):
    ts = now_iso()
    rxcui = concept["rxcui"]

    db.run("""
        MERGE (d:Drug {source: 'rxnorm', source_id: $rxcui})
        ON CREATE SET
            d.codex_id = 'codex-drug-RX' + $rxcui,
            d.canonical_name = $name,
            d.drug_type = 'small_molecule',
            d.is_approved = true,
            d.source_attribute_name = 'rxcui',
            d.created_at = datetime($ts),
            d.updated_at = datetime($ts)
        ON MATCH SET d.updated_at = datetime($ts)
    """, {"rxcui": rxcui, "name": concept["name"], "ts": ts})

    db.run("""
    MERGE (ds:DataSource {name: 'rxnorm'})
    """)

    db.run("""
        MATCH (d:Drug {source: 'rxnorm', source_id: $rxcui})
        MATCH (ds:DataSource {name: 'rxnorm'})
        MERGE (d)-[:SOURCED_FROM {
            ingested_at: datetime($ts)
        }]->(ds)
    """, {"rxcui": rxcui, "ts": ts})

    # DrugName creation (same as before)
    for rel in concept.get("related_concepts", []):
        if rel["tty"] in ("SCD", "SBD"):
            db.run("""
                MERGE (dn:DrugName {name: $name, country: 'US', language: 'en'})
                ON CREATE SET
                    dn.name_type = $name_type,
                    dn.source = 'rxnorm',
                    dn.created_at = datetime($ts),
                    dn.updated_at = datetime($ts)
                ON MATCH SET dn.updated_at = datetime($ts)
            """, {
                "name": rel["name"],
                "name_type": "clinical_dose_form" if rel["tty"] == "SCD" else "brand_dose_form",
                "ts": ts
            })

            db.run("""
                MATCH (d:Drug {source: 'rxnorm', source_id: $rxcui})
                MATCH (dn:DrugName {name: $name})
                MERGE (d)-[:HAS_NAME]->(dn)
            """, {"rxcui": rxcui, "name": rel["name"]})

def ensure_rxnorm_drug(db, drug_name):
    # Step 1: check if already exists
    result = list(db.run("""
    MATCH (d:Drug)
    WHERE toLower(d.canonical_name) = toLower($name)
    RETURN d LIMIT 1
""", {"name": drug_name}))

    if result:
        return  # already in DB

    # Step 2: fetch from API
    concept = fetch_single_rxnorm(drug_name)

    if not concept:
        print(f"[RxNorm] Not found: {drug_name}")
        return

    # Step 3: insert into Neo4j
    insert_rxnorm_concept(db, concept)

    print(f"[RxNorm] On-demand loaded: {drug_name}")

def load_rxnorm(db, poc_ids: set = None):
    drug_list = [
    "Acetaminophen", "Aspirin", "Metformin",
    "Warfarin", "Methotrexate",
    "Ibuprofen", "Amoxicillin", "Lisinopril"
    ]

    concepts = fetch_rxnorm_concepts(drug_list)

    if poc_ids is None:
        poc_ids = {"161", "1191", "6809"}   # Acetaminophen, Aspirin, Metformin

    print(f"[RxNorm] Loading {len(concepts)} concepts...")

    for concept in concepts:
        rxcui   = concept["rxcui"]
        is_poc  = rxcui in poc_ids
        ts      = now_iso()

        # ---- Upsert Drug node ----
        db.run("""
            MERGE (d:Drug {source: 'rxnorm', source_id: $rxcui})
            ON CREATE SET
                d.codex_id             = 'codex-drug-RX' + $rxcui,
                d.canonical_name       = $name,
                d.drug_type            = 'small_molecule',
                d.is_approved          = true,
                d.source_attribute_name = 'rxcui',
                d.created_at           = datetime($ts),
                d.updated_at           = datetime($ts),
                d.is_poc               = $is_poc
            ON MATCH SET
                d.updated_at           = datetime($ts)
        """, {"rxcui": rxcui, "name": concept["name"], "ts": ts, "is_poc": is_poc})

        # ---- SOURCED_FROM ----
        db.run("""
            MATCH (d:Drug {source: 'rxnorm', source_id: $rxcui})
            MATCH (ds:DataSource {name: 'rxnorm'})
            MERGE (d)-[:SOURCED_FROM {ingested_at: datetime($ts)}]->(ds)
        """, {"rxcui": rxcui, "ts": ts})

        # ---- EQUIVALENT_TO DrugBank ----
        if rxcui in RXCUI_TO_DRUGBANK:
            db_id = RXCUI_TO_DRUGBANK[rxcui]
            db.run("""
                MATCH (db_drug:Drug {source: 'drugbank', source_id: $db_id})
                MATCH (rx_drug:Drug {source: 'rxnorm', source_id: $rxcui})
                MERGE (db_drug)-[:EQUIVALENT_TO {
                    confidence: 1.0,
                    source: 'codex-normalization',
                    match_basis: 'name+inchikey',
                    created_at: datetime($ts)
                }]->(rx_drug)
            """, {"db_id": db_id, "rxcui": rxcui, "ts": ts})

        # ---- Clinical dose form names (SCD/SBD) ----
        for rel in concept.get("related_concepts", []):
            if rel["tty"] in ("SCD", "SBD"):
                db.run("""
                    MERGE (dn:DrugName {name: $name, country: 'US', language: 'en'})
                    ON CREATE SET
                        dn.name_type           = $name_type,
                        dn.is_primary          = false,
                        dn.source              = 'rxnorm',
                        dn.source_attribute_name = $tty,
                        dn.created_at          = datetime($ts),
                        dn.updated_at          = datetime($ts),
                        dn.is_poc              = false
                    ON MATCH SET dn.updated_at = datetime($ts)
                """, {
                    "name":      rel["name"],
                    "name_type": "clinical_dose_form" if rel["tty"] == "SCD" else "brand_dose_form",
                    "tty":       rel["tty"],
                    "ts":        ts,
                })

                db.run("""
                    MATCH (d:Drug {source: 'rxnorm', source_id: $rxcui})
                    MATCH (dn:DrugName {name: $name, country: 'US', language: 'en'})
                    MERGE (d)-[:HAS_NAME {source: 'rxnorm', created_at: datetime($ts)}]->(dn)
                """, {"rxcui": rxcui, "name": rel["name"], "ts": ts})

        print(f"  [RxNorm] Loaded: {concept['name']} (RxCUI {rxcui})" +
              (" [POC]" if is_poc else ""))

    print(f"[RxNorm] Done. {len(concepts)} concepts processed.\n")
