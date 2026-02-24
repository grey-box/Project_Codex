"""
Project Codex — RxNorm Source Loader
Reads sample_data/rxnorm_sample.json and maps into normalized Codex schema.
RxNorm is US-centric; creates EQUIVALENT_TO links to DrugBank nodes.
"""

import json
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


def load_rxnorm(db, data_path: str, poc_ids: set = None):
    with open(data_path) as f:
        concepts = json.load(f)

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
