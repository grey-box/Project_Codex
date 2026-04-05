"""
Project Codex — Full ETL Pipeline Runner
Runs all four source loaders in the correct order:
  0. Setup constraints + indexes
  1. DrugBank
  2. RxNorm
  3. ICD-11
  4. SNOMED CT

Usage:
    python scripts/run_etl.py

Requirements:
    pip install neo4j
    Neo4j running at bolt://localhost:7687 (see scripts/config.py)
"""

import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import CodexDB
from config import SAMPLE_DATA_DIR, CYPHER_DIR
from loaders.drugbank_loader  import load_drugbank
from loaders.rxnorm_loader    import load_rxnorm, ensure_rxnorm_drug
from loaders.icd11_loader     import load_icd11
from loaders.snomedct_loader  import load_snomedct


SETUP_FILE = os.path.join(CYPHER_DIR, "00_setup_constraints.cypher")


def run():
    print("=" * 60)
    print("  Project Codex — Neo4j ETL Pipeline")
    print("=" * 60)

    with CodexDB() as db:

        # Step 0: Schema setup
        print("\n[Step 0] Setting up constraints and indexes...")
        n = db.run_file(SETUP_FILE)
        print(f"  Executed {n} statements from setup file.\n")

        # Step 1: DrugBank
        print("[Step 1] Loading DrugBank...")
        load_drugbank(db, os.path.join(SAMPLE_DATA_DIR, "drugbank_sample.json"))

        # Step 2: RxNorm
        print("[Step 2] Loading RxNorm...")
        load_rxnorm(db)
        print("[Step 2.5] Testing on-demand RxNorm fetch...")
        ensure_rxnorm_drug(db, "Simvastatin")
        ensure_rxnorm_drug(db, "Atorvastatin")
        # Step 3: ICD-11
        print("[Step 3] Loading ICD-11...")
        load_icd11(db, os.path.join(SAMPLE_DATA_DIR, "icd11_sample.json"))

        # Step 4: SNOMED CT
        print("[Step 4] Loading SNOMED CT...")
        load_snomedct(db, os.path.join(SAMPLE_DATA_DIR, "snomedct_sample.json"))

        # Summary
        print("=" * 60)
        print("  ETL Complete — Summary")
        print("=" * 60)
        summary = db.run("""
            MATCH (d:Drug)    WITH count(d) AS drugs
            MATCH (dn:DrugName) WITH drugs, count(dn) AS names
            MATCH (c:Condition) WITH drugs, names, count(c) AS conds
            MATCH (i:Ingredient) WITH drugs, names, conds, count(i) AS ings
            RETURN drugs, names, conds, ings
        """)
        if summary:
            r = summary[0]
            print(f"  Drug nodes:       {r.get('drugs', '?')}")
            print(f"  DrugName nodes:   {r.get('names', '?')}")
            print(f"  Condition nodes:  {r.get('conds', '?')}")
            print(f"  Ingredient nodes: {r.get('ings', '?')}")

        poc_count = db.run("MATCH (d:Drug {is_poc: true}) RETURN count(d) AS n")
        if poc_count:
            print(f"  POC drugs:        {poc_count[0]['n']}")

        print("\n  Run cypher/05_demo_queries.cypher in Neo4j Browser to explore!")
        print("=" * 60)

        db.run_file("cypher/05_demo_queries.cypher")


if __name__ == "__main__":
    run()
