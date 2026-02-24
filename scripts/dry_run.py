"""
Project Codex — Dry Run (no Neo4j required)
Validates sample data and shows what would be loaded.
Run this without a Neo4j connection to verify data quality.

Usage:
    python scripts/dry_run.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import SAMPLE_DATA_DIR


def load_json(filename):
    path = os.path.join(SAMPLE_DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


def section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def dry_run():
    print("\nProject Codex — ETL Dry Run")
    print("Validating sample data files...\n")

    # ---- DrugBank ----
    section("DrugBank Sample Data")
    drugbank = load_json("drugbank_sample.json")
    print(f"  Records: {len(drugbank)}")
    total_brands = 0
    for d in drugbank:
        brands = d.get("brands", [])
        total_brands += len(brands)
        countries = [b["country"] for b in brands]
        print(f"  [{d['drugbank_id']}] {d['name']:<20} → {len(brands)} brand names: {countries}")
    print(f"  Total brand-name nodes to create: {total_brands}")

    # ---- RxNorm ----
    section("RxNorm Sample Data")
    rxnorm = load_json("rxnorm_sample.json")
    print(f"  Records: {len(rxnorm)}")
    for r in rxnorm:
        dose_forms = [c["name"] for c in r.get("related_concepts", []) if c["tty"] in ("SCD","SBD")]
        print(f"  [RxCUI {r['rxcui']:>6}] {r['name']:<20} → {len(dose_forms)} dose-form names")

    # ---- ICD-11 ----
    section("ICD-11 Sample Data")
    icd11 = load_json("icd11_sample.json")
    print(f"  Records: {len(icd11)}")
    for c in icd11:
        syns = c.get("synonyms", [])
        print(f"  [{c['code']:<8}] {c['title']:<40} | Chapter {c['chapter']}: {c['chapter_title'][:30]}")
        if syns:
            print(f"             Synonyms: {', '.join(syns)}")

    # ---- SNOMED CT ----
    section("SNOMED CT Sample Data")
    snomed = load_json("snomedct_sample.json")
    print(f"  Records: {len(snomed)}")
    for c in snomed:
        descs = [d["term"] for d in c.get("descriptions", []) if d["type"] == "Synonym"]
        print(f"  [{c['concept_id']}] ({c['semantic_tag']:<10}) {c['preferred_term']}")
        if descs:
            print(f"    Synonyms: {', '.join(descs)}")

    # ---- Codex Name Translation Preview ----
    section("Codex Name Translation Preview")
    print("  Drug: Acetaminophen (DB00316)")
    print("  All regional names found across all sources:\n")

    name_map = {}
    # From DrugBank
    apap = next(d for d in drugbank if d["drugbank_id"] == "DB00316")
    for b in apap["brands"]:
        name_map[b["country"]] = b["name"]
    name_map["US (generic)"] = apap["name"]

    # From SNOMED (Paracetamol)
    paracetamol = next(c for c in snomed if c["concept_id"] == "387517004")
    for desc in paracetamol["descriptions"]:
        if desc["term"] == "Paracetamol":
            for country in ["GB", "IN", "AU"]:
                if country not in name_map:
                    name_map[country] = "Paracetamol"

    print(f"  {'Country/Region':<20} {'Name'}")
    print(f"  {'-'*20} {'-'*20}")
    for region, name in sorted(name_map.items()):
        print(f"  {region:<20} {name}")

    # ---- Schema Summary ----
    section("Estimated Graph Size (after full load)")
    drug_nodes = len(set(d["drugbank_id"] for d in drugbank))
    drug_nodes += len(rxnorm)    # RxNorm Drug nodes
    drug_nodes += len([c for c in snomed if c["semantic_tag"] == "substance"])
    cond_nodes  = len(icd11) + len([c for c in snomed if c["semantic_tag"] == "disorder"])
    name_nodes  = total_brands + len(rxnorm) * 2  # approx
    print(f"  ~{drug_nodes:>4} Drug nodes")
    print(f"  ~{name_nodes:>4} DrugName nodes")
    print(f"  ~{cond_nodes:>4} Condition nodes")
    print(f"  ~  4 DataSource nodes")
    print(f"  ~  5 Ingredient nodes")
    print()
    print("  POC-flagged drugs (for dev/demo/debug):")
    poc_names = [d["name"] for d in drugbank[:3]]
    for n in poc_names:
        print(f"    ✓ {n}")

    print("\nDry run complete. No database connection required.")
    print("Run scripts/run_etl.py to load into Neo4j.\n")


if __name__ == "__main__":
    dry_run()
