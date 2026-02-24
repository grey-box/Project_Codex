"""
Project Codex — ICD-11 Source Loader
Reads sample_data/icd11_sample.json and loads conditions into Codex schema.
"""

import json
from datetime import datetime, timezone

# Map ICD-11 codes to DrugBank drug IDs for TREATS relationships
ICD11_TREATS_DRUGBANK = {
    "JA00": ["DB00331"],          # T2DM ← Metformin
    "BA00": [],                    # Hypertension (drugs loaded separately)
    "CA01": ["DB00682", "DB00945"], # AF ← Warfarin, Aspirin
    "FA24": ["DB00563"],           # RA ← Methotrexate
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_icd11(db, data_path: str, poc_codes: set = None):
    with open(data_path) as f:
        conditions = json.load(f)

    if poc_codes is None:
        poc_codes = {"JA00", "BA00", "FA24"}

    print(f"[ICD-11] Loading {len(conditions)} conditions...")

    for cond in conditions:
        code   = cond["code"]
        is_poc = code in poc_codes
        ts     = now_iso()

        # ---- Upsert Condition node ----
        db.run("""
            MERGE (c:Condition {source: 'icd11', source_id: $code})
            ON CREATE SET
                c.codex_id             = 'codex-cond-ICD-' + $code,
                c.canonical_name       = $name,
                c.icd11_code           = $code,
                c.source_attribute_name = 'code',
                c.created_at           = datetime($ts),
                c.updated_at           = datetime($ts),
                c.is_poc               = $is_poc
            ON MATCH SET
                c.updated_at           = datetime($ts)
        """, {"code": code, "name": cond["title"], "ts": ts, "is_poc": is_poc})

        # ---- SOURCED_FROM ----
        db.run("""
            MATCH (c:Condition {source: 'icd11', source_id: $code})
            MATCH (ds:DataSource {name: 'icd11'})
            MERGE (c)-[:SOURCED_FROM {ingested_at: datetime($ts)}]->(ds)
        """, {"code": code, "ts": ts})

        # ---- TREATS relationships ----
        for drug_id in ICD11_TREATS_DRUGBANK.get(code, []):
            db.run("""
                MATCH (d:Drug {source: 'drugbank', source_id: $drug_id})
                MATCH (c:Condition {source: 'icd11', source_id: $code})
                MERGE (d)-[:TREATS {
                    evidence_level: 'A',
                    source: 'icd11+drugbank',
                    created_at: datetime($ts)
                }]->(c)
            """, {"drug_id": drug_id, "code": code, "ts": ts})

        print(f"  [ICD-11] Loaded: {cond['title']} ({code})" +
              (" [POC]" if is_poc else ""))

    # ---- ICD-11 hierarchy (PARENT_OF) ----
    hierarchy = [
        ("BA00", "CA01"),   # Circulatory diseases → Atrial fibrillation
    ]
    for parent_code, child_code in hierarchy:
        db.run("""
            MATCH (parent:Condition {source: 'icd11', source_id: $parent})
            MATCH (child:Condition  {source: 'icd11', source_id: $child})
            MERGE (parent)-[:PARENT_OF {source: 'icd11'}]->(child)
        """, {"parent": parent_code, "child": child_code})

    print(f"[ICD-11] Done. {len(conditions)} conditions processed.\n")
