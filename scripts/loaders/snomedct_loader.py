"""
Project Codex — SNOMED CT Source Loader
Reads sample_data/snomedct_sample.json and loads into Codex schema.
Establishes EQUIVALENT_TO links between SNOMED and DrugBank/ICD-11 nodes.
"""

import json
from datetime import datetime, timezone

# SNOMED concept_id → DrugBank ID (for EQUIVALENT_TO)
SNOMED_TO_DRUGBANK = {
    "387517004": "DB00316",   # Paracetamol ↔ Acetaminophen
    "387458008": "DB00945",   # Aspirin
    "387467008": "DB00331",   # Metformin
    "372687004": None,        # Amoxicillin — not yet in DrugBank sample
}

# SNOMED concept_id → ICD-11 code (for conditions)
SNOMED_DISORDER_TO_ICD11 = {
    "44508008": "JA00",   # T2DM
    "69896004": "FA24",   # Rheumatoid arthritis
}

# Names to add as DrugName nodes (SNOMED synonyms)
SNOMED_NAMES = {
    "387517004": [
        {"name": "Paracetamol", "country": "GB", "language": "en", "name_type": "generic"},
        {"name": "Paracetamol", "country": "IN", "language": "en", "name_type": "generic"},
        {"name": "Paracetamol", "country": "AU", "language": "en", "name_type": "generic"},
        {"name": "Paracetamol", "country": "ZA", "language": "en", "name_type": "generic"},
    ],
    "387458008": [
        {"name": "Acetylsalicylic acid", "country": "US", "language": "en", "name_type": "generic"},
    ],
    "372687004": [
        {"name": "Amoxicillin", "country": "US", "language": "en", "name_type": "generic"},
        {"name": "Amoxil",      "country": "US", "language": "en", "name_type": "brand"},
        {"name": "Amoxicillin", "country": "IN", "language": "hi", "name_type": "generic"},
        {"name": "Mox",         "country": "IN", "language": "hi", "name_type": "brand"},
    ],
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_snomedct(db, data_path: str, poc_ids: set = None):
    with open(data_path) as f:
        concepts = json.load(f)

    if poc_ids is None:
        poc_ids = {"387517004", "387458008", "387467008", "44508008", "69896004"}

    print(f"[SNOMED CT] Loading {len(concepts)} concepts...")

    for concept in concepts:
        cid     = concept["concept_id"]
        is_poc  = cid in poc_ids
        ts      = now_iso()
        tag     = concept["semantic_tag"]

        if tag == "substance":
            _load_snomed_drug(db, concept, cid, is_poc, ts)
        elif tag == "disorder":
            _load_snomed_condition(db, concept, cid, is_poc, ts)

        print(f"  [SNOMED CT] Loaded: {concept['preferred_term']} ({cid}, {tag})" +
              (" [POC]" if is_poc else ""))

    print(f"[SNOMED CT] Done. {len(concepts)} concepts processed.\n")


def _load_snomed_drug(db, concept, cid, is_poc, ts):
    db.run("""
        MERGE (d:Drug {source: 'snomedct', source_id: $cid})
        ON CREATE SET
            d.codex_id             = 'codex-drug-SCT' + $cid,
            d.canonical_name       = $name,
            d.drug_type            = 'small_molecule',
            d.is_approved          = true,
            d.source_attribute_name = 'concept_id',
            d.created_at           = datetime($ts),
            d.updated_at           = datetime($ts),
            d.is_poc               = $is_poc
        ON MATCH SET d.updated_at = datetime($ts)
    """, {"cid": cid, "name": concept["preferred_term"], "ts": ts, "is_poc": is_poc})

    db.run("""
        MATCH (d:Drug {source: 'snomedct', source_id: $cid})
        MATCH (ds:DataSource {name: 'snomedct'})
        MERGE (d)-[:SOURCED_FROM {ingested_at: datetime($ts)}]->(ds)
    """, {"cid": cid, "ts": ts})

    # Add SNOMED-specific name variants
    for nm in SNOMED_NAMES.get(cid, []):
        db.run("""
            MERGE (dn:DrugName {name: $name, country: $country, language: $language})
            ON CREATE SET
                dn.name_type           = $name_type,
                dn.is_primary          = true,
                dn.source              = 'snomedct',
                dn.source_attribute_name = 'descriptions.Synonym',
                dn.created_at          = datetime($ts),
                dn.updated_at          = datetime($ts),
                dn.is_poc              = $is_poc
            ON MATCH SET dn.updated_at = datetime($ts)
        """, {**nm, "ts": ts, "is_poc": is_poc})

        db.run("""
            MATCH (d:Drug {source: 'snomedct', source_id: $cid})
            MATCH (dn:DrugName {name: $name, country: $country, language: $language})
            MERGE (d)-[:HAS_NAME {source: 'snomedct', created_at: datetime($ts)}]->(dn)
        """, {"cid": cid, "name": nm["name"], "country": nm["country"],
              "language": nm["language"], "ts": ts})

    # EQUIVALENT_TO DrugBank
    db_id = SNOMED_TO_DRUGBANK.get(cid)
    if db_id:
        db.run("""
            MATCH (db_drug:Drug {source: 'drugbank', source_id: $db_id})
            MATCH (sct_drug:Drug {source: 'snomedct', source_id: $cid})
            MERGE (db_drug)-[:EQUIVALENT_TO {
                confidence: 1.0,
                source: 'codex-normalization',
                match_basis: 'inchikey',
                created_at: datetime($ts)
            }]->(sct_drug)
        """, {"db_id": db_id, "cid": cid, "ts": ts})


def _load_snomed_condition(db, concept, cid, is_poc, ts):
    db.run("""
        MERGE (c:Condition {source: 'snomedct', source_id: $cid})
        ON CREATE SET
            c.codex_id             = 'codex-cond-SCT' + $cid,
            c.canonical_name       = $name,
            c.snomed_id            = $cid,
            c.source_attribute_name = 'concept_id',
            c.created_at           = datetime($ts),
            c.updated_at           = datetime($ts),
            c.is_poc               = $is_poc
        ON MATCH SET c.updated_at = datetime($ts)
    """, {"cid": cid, "name": concept["preferred_term"], "ts": ts, "is_poc": is_poc})

    db.run("""
        MATCH (c:Condition {source: 'snomedct', source_id: $cid})
        MATCH (ds:DataSource {name: 'snomedct'})
        MERGE (c)-[:SOURCED_FROM {ingested_at: datetime($ts)}]->(ds)
    """, {"cid": cid, "ts": ts})

    # EQUIVALENT_TO ICD-11 condition
    icd_code = SNOMED_DISORDER_TO_ICD11.get(cid)
    if icd_code:
        db.run("""
            MATCH (icd:Condition {source: 'icd11', source_id: $icd_code})
            MATCH (sct:Condition {source: 'snomedct', source_id: $cid})
            MERGE (icd)-[:EQUIVALENT_TO {
                confidence: 1.0,
                source: 'codex-normalization',
                match_basis: 'clinical-mapping',
                created_at: datetime($ts)
            }]->(sct)
        """, {"icd_code": icd_code, "cid": cid, "ts": ts})

        # Enrich ICD-11 condition with SNOMED ID
        db.run("""
            MATCH (c:Condition {source: 'icd11', source_id: $icd_code})
            SET c.snomed_id = $cid
        """, {"icd_code": icd_code, "cid": cid})
