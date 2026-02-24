# Project Codex — Neo4j Schema Normalization

> Translate medicine names across countries and languages using a unified graph database.
> (e.g., Tylenol in the US → Dolo in India → Panadol in the UK → Dafalgan in France)

---

## Task: Normalize Neo4j Schema

This repository delivers the normalized schema for Project Codex's Neo4j graph database,
unifying four pharmaceutical/clinical data sources into a single, extensible schema.

---

## Sources Normalized

| #   | Source   | Coverage                       | Primary Key       |
| --- | -------- | ------------------------------ | ----------------- |
| 1   | DrugBank | Drug compounds, interactions   | DrugBank ID       |
| 2   | ICD-11   | Disease/condition codes (WHO)  | ICD-11 code       |
| 3   | RxNorm   | Clinical drug naming (US, NLM) | RxCUI             |
| 4   | SnomedCT | Clinical terminology (global)  | SNOMED Concept ID |

---

## Codex Schema Design Decisions

### 1. Source Provenance (required by task)

Every node carries three provenance fields:

- **`source`** — which system the record came from (`drugbank`, `rxnorm`, `icd11`, `snomedct`)
- **`source_id`** — the original primary key in that system (e.g., `DB00316`, `RxCUI 161`)
- **`source_attribute_name`** — the original field name in that source's schema (e.g., `drugbank_id`, `rxcui`, `code`)

### 2. Timestamps (required by task)

- **`created_at`** — set once at first ingestion, never overwritten
- **`updated_at`** — updated on every data refresh cycle via `ON MATCH SET`

### 3. POC Flag (required by task)

- **`is_poc: true`** on nodes included in the small dev/demo/debug subset
- Filter any query to POC data: `WHERE n.is_poc = true`
- Default POC set: Acetaminophen, Aspirin, Metformin (and their names/conditions)

### 4. Core Codex Use Case — Medicine Translation

- `:Drug` → `HAS_NAME` → `:DrugName` with `country` + `language` properties
- `EQUIVALENT_TO` links drugs that are the same compound across sources
  (e.g., DrugBank Acetaminophen ↔ SNOMED Paracetamol ↔ RxNorm RxCUI 161)

### 5. Extensible for Future Sources

- New sources add their own `source` value — no schema changes needed
- New node types can be added without breaking existing queries
- `:DataSource` nodes track all registered sources with version + refresh date

---

## Quick Start

### Option A — Dry run (no Neo4j needed)

Validates all sample data and previews what will be loaded:

```bash
python scripts/dry_run.py
```

### Option B — Load into Neo4j

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Configure connection** — edit `scripts/config.py`:

```python
NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "your-password"
```

**3. Run the ETL pipeline**

```bash
python scripts/run_etl.py
```

**4. Explore in Neo4j Browser**
Open `http://localhost:7474` and run queries from `cypher/05_demo_queries.cypher`.

### Option C — Run Cypher files directly in Neo4j Browser

Copy-paste in order:

1. `cypher/00_setup_constraints.cypher`
2. `cypher/01_load_drugbank.cypher`
3. `cypher/02_load_rxnorm.cypher`
4. `cypher/03_load_icd11.cypher`
5. `cypher/04_load_snomedct.cypher`
6. `cypher/05_demo_queries.cypher` (demo)

---

## Key Demo Query — Medicine Translation

```cypher
// What is Tylenol called in India, France, and Germany?
MATCH (d:Drug)-[:HAS_NAME]->(us:DrugName {name: 'Tylenol', country: 'US'})
MATCH (d)-[:HAS_NAME]->(intl:DrugName)
WHERE intl.country <> 'US'
RETURN d.canonical_name AS drug,
       intl.name        AS name,
       intl.country     AS country,
       intl.language    AS language
ORDER BY intl.country;
```

Expected result:

| drug          | name        | country | language |
| ------------- | ----------- | ------- | -------- |
| Acetaminophen | Ben-u-ron   | DE      | de       |
| Acetaminophen | Dafalgan    | FR      | fr       |
| Acetaminophen | Panadol     | GB      | en       |
| Acetaminophen | Dolo        | IN      | hi       |
| Acetaminophen | Paracetamol | AU      | en       |

---

## What's In the Sample Data

| Drug          | US Name    | India Name | UK Name | France Name | Germany Name |
| ------------- | ---------- | ---------- | ------- | ----------- | ------------ |
| Acetaminophen | Tylenol    | Dolo       | Panadol | Dafalgan    | Ben-u-ron    |
| Aspirin       | Aspirin    | Disprin    | Aspirin | —           | ASS          |
| Metformin     | Glucophage | Glycomet   | —       | —           | Siofor       |
| Warfarin      | Coumadin   | Warf       | Marevan | —           | —            |
| Methotrexate  | Trexall    | Folitrax   | —       | Methofar    | Lantarel     |

---

## Requirements

```
neo4j>=5.0
```
