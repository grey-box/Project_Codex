"""
Project Codex — DrugBank Source Loader
Reads sample_data/drugbank_sample.json and writes into normalized Codex schema.
"""

import json
import uuid
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_drugbank(db, data_path: str, poc_ids: set = None):
    """
    Load DrugBank JSON sample data into Neo4j.

    Args:
        db:         CodexDB instance
        data_path:  Path to drugbank_sample.json
        poc_ids:    Set of DrugBank IDs to flag as POC (default: first 3)
    """
    with open(data_path) as f:
        drugs = json.load(f)

    if poc_ids is None:
        poc_ids = {d["drugbank_id"] for d in drugs[:3]}

    print(f"[DrugBank] Loading {len(drugs)} drugs...")

    for drug in drugs:
        db_id   = drug["drugbank_id"]
        is_poc  = db_id in poc_ids
        ts      = now_iso()

        # ---- Upsert Drug node ----
        db.run("""
            MERGE (d:Drug {source: 'drugbank', source_id: $source_id})
            ON CREATE SET
                d.codex_id             = $codex_id,
                d.canonical_name       = $name,
                d.drug_type            = $drug_type,
                d.is_approved          = $is_approved,
                d.source_attribute_name = 'drugbank_id',
                d.created_at           = datetime($ts),
                d.updated_at           = datetime($ts),
                d.is_poc               = $is_poc
            ON MATCH SET
                d.updated_at           = datetime($ts)
        """, {
            "source_id":  db_id,
            "codex_id":   "codex-drug-" + db_id,
            "name":       drug["name"],
            "drug_type":  drug.get("type", "small molecule").replace(" ", "_"),
            "is_approved": "approved" in drug.get("groups", []),
            "ts":         ts,
            "is_poc":     is_poc,
        })

        # ---- Upsert Ingredient node ----
        if drug.get("inchikey"):
            db.run("""
                MERGE (i:Ingredient {inchikey: $inchikey})
                ON CREATE SET
                    i.codex_id             = $codex_id,
                    i.name                 = $name,
                    i.cas_number           = $cas_number,
                    i.source               = 'drugbank',
                    i.source_id            = $source_id,
                    i.source_attribute_name = 'cas_number',
                    i.created_at           = datetime($ts),
                    i.updated_at           = datetime($ts),
                    i.is_poc               = $is_poc
                ON MATCH SET i.updated_at = datetime($ts)
            """, {
                "inchikey":    drug["inchikey"],
                "codex_id":    "codex-ing-" + drug["inchikey"][:8],
                "name":        drug["name"],
                "cas_number":  drug.get("cas_number", ""),
                "source_id":   db_id + "-active",
                "ts":          ts,
                "is_poc":      is_poc,
            })

            db.run("""
                MATCH (d:Drug {source: 'drugbank', source_id: $db_id})
                MATCH (i:Ingredient {inchikey: $inchikey})
                MERGE (d)-[:CONTAINS_INGREDIENT {role: 'active', source: 'drugbank'}]->(i)
            """, {"db_id": db_id, "inchikey": drug["inchikey"]})

        # ---- Upsert DrugName nodes ----
        for brand in drug.get("brands", []):
            db.run("""
                MERGE (dn:DrugName {name: $name, country: $country, language: $language})
                ON CREATE SET
                    dn.name_type           = 'brand',
                    dn.is_primary          = true,
                    dn.source              = 'drugbank',
                    dn.source_attribute_name = 'brands.name',
                    dn.created_at          = datetime($ts),
                    dn.updated_at          = datetime($ts),
                    dn.is_poc              = $is_poc
                ON MATCH SET dn.updated_at = datetime($ts)
            """, {
                "name":     brand["name"],
                "country":  brand["country"],
                "language": _country_to_lang(brand["country"]),
                "ts":       ts,
                "is_poc":   is_poc,
            })

            db.run("""
                MATCH (d:Drug {source: 'drugbank', source_id: $db_id})
                MATCH (dn:DrugName {name: $name, country: $country})
                MERGE (d)-[:HAS_NAME {source: 'drugbank', created_at: datetime($ts)}]->(dn)
            """, {"db_id": db_id, "name": brand["name"],
                  "country": brand["country"], "ts": ts})

        # ---- Generic name entry (US, EN) ----
        db.run("""
            MERGE (dn:DrugName {name: $name, country: 'US', language: 'en'})
            ON CREATE SET
                dn.name_type           = 'generic',
                dn.is_primary          = true,
                dn.source              = 'drugbank',
                dn.source_attribute_name = 'name',
                dn.created_at          = datetime($ts),
                dn.updated_at          = datetime($ts),
                dn.is_poc              = $is_poc
            ON MATCH SET dn.updated_at = datetime($ts)
        """, {"name": drug["name"], "ts": ts, "is_poc": is_poc})

        db.run("""
            MATCH (d:Drug {source: 'drugbank', source_id: $db_id})
            MATCH (dn:DrugName {name: $name, country: 'US', language: 'en'})
            MERGE (d)-[:HAS_NAME {source: 'drugbank', created_at: datetime($ts)}]->(dn)
        """, {"db_id": db_id, "name": drug["name"], "ts": ts})

        # ---- SOURCED_FROM ----
        db.run("""
            MATCH (d:Drug {source: 'drugbank', source_id: $db_id})
            MATCH (ds:DataSource {name: 'drugbank'})
            MERGE (d)-[:SOURCED_FROM {ingested_at: datetime($ts)}]->(ds)
        """, {"db_id": db_id, "ts": ts})

        print(f"  [DrugBank] Loaded: {drug['name']} ({db_id})" +
              (" [POC]" if is_poc else ""))

    print(f"[DrugBank] Done. {len(drugs)} drugs processed.\n")


def _country_to_lang(country: str) -> str:
    mapping = {
        "US": "en", "GB": "en", "AU": "en", "IN": "hi",
        "FR": "fr", "DE": "de", "IT": "it", "ES": "es",
        "JP": "ja", "CN": "zh",
    }
    return mapping.get(country, "en")
