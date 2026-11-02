# Project Codex — Normalized Neo4j Schema Design

## Overview

Project Codex maps medicine names across countries and languages (e.g., Tylenol in US → Dolo in India). This schema normalizes four heterogeneous pharmaceutical/clinical data sources into a single, extensible graph schema.

---

## Sources Being Normalized

| Source     | Focus                              | Primary ID Type       |
|------------|------------------------------------|-----------------------|
| DrugBank   | Drug compounds, interactions       | DrugBank ID (DB#####) |
| ICD-11     | Disease & condition coding         | ICD-11 code           |
| RxNorm     | Clinical drug naming (US)          | RxCUI                 |
| SnomedCT   | Clinical terminology               | SNOMED Concept ID     |

---

## Normalized Node Labels

### `:Drug`
The central node representing a unified drug/medicine concept.

| Property               | Type      | Description                                      |
|------------------------|-----------|--------------------------------------------------|
| `codex_id`             | String    | Internal Codex UUID (primary key)                |
| `canonical_name`       | String    | Preferred English name                           |
| `drug_type`            | String    | `small_molecule`, `biologic`, `vaccine`, etc.    |
| `is_approved`          | Boolean   | Whether the drug has regulatory approval         |
| `source`               | String    | Source system name (`drugbank`, `rxnorm`, etc.)  |
| `source_id`            | String    | Original ID in the source system                 |
| `source_attribute_name`| String    | Original attribute/field name in source schema   |
| `created_at`           | DateTime  | When this record was first ingested              |
| `updated_at`           | DateTime  | Last refresh/sync timestamp                      |
| `is_poc`               | Boolean   | Flag: included in POC subset (demo/debug)        |

---

### `:DrugName`
Represents a regional/linguistic name for a drug (brand, generic, or common).

| Property               | Type      | Description                                      |
|------------------------|-----------|--------------------------------------------------|
| `name`                 | String    | The name string                                  |
| `name_type`            | String    | `brand`, `generic`, `common`, `international`    |
| `language`             | String    | ISO 639-1 language code (e.g., `en`, `hi`, `de`) |
| `country`              | String    | ISO 3166 country code (e.g., `US`, `IN`, `DE`)   |
| `is_primary`           | Boolean   | Whether this is the primary name in that locale  |
| `source`               | String    | Source system that provided this name            |
| `source_attribute_name`| String    | Original field name in source schema             |
| `created_at`           | DateTime  | Ingestion timestamp                              |
| `updated_at`           | DateTime  | Last refresh timestamp                           |
| `is_poc`               | Boolean   | POC subset flag                                  |

---

### `:Condition`
A medical condition, disease, or indication.

| Property               | Type      | Description                                      |
|------------------------|-----------|--------------------------------------------------|
| `codex_id`             | String    | Internal Codex UUID                              |
| `canonical_name`       | String    | Preferred English term                           |
| `icd11_code`           | String    | ICD-11 code if available                         |
| `snomed_id`            | String    | SNOMED CT concept ID if available                |
| `source`               | String    | Source system                                    |
| `source_id`            | String    | Original ID in source                            |
| `source_attribute_name`| String    | Original field name in source                    |
| `created_at`           | DateTime  | Ingestion timestamp                              |
| `updated_at`           | DateTime  | Last refresh timestamp                           |
| `is_poc`               | Boolean   | POC subset flag                                  |

---

### `:Ingredient`
An active or inactive pharmaceutical ingredient.

| Property               | Type      | Description                                      |
|------------------------|-----------|--------------------------------------------------|
| `codex_id`             | String    | Internal Codex UUID                              |
| `name`                 | String    | IUPAC or common name                             |
| `cas_number`           | String    | CAS Registry Number                              |
| `inchikey`             | String    | InChI Key (structure hash)                       |
| `source`               | String    | Source system                                    |
| `source_id`            | String    | Original ID in source                            |
| `source_attribute_name`| String    | Original field name in source                    |
| `created_at`           | DateTime  | Ingestion timestamp                              |
| `updated_at`           | DateTime  | Last refresh timestamp                           |
| `is_poc`               | Boolean   | POC subset flag                                  |

---

### `:DataSource`
Metadata about the upstream data source itself.

| Property               | Type      | Description                                      |
|------------------------|-----------|--------------------------------------------------|
| `name`                 | String    | Source name (`drugbank`, `icd11`, `rxnorm`, etc.)|
| `version`              | String    | Data version ingested                            |
| `last_refreshed`       | DateTime  | Most recent full refresh                         |
| `url`                  | String    | Source URL                                       |
| `license`              | String    | Data license type                                |

---

## Relationships

| Relationship               | From          | To            | Properties                          |
|----------------------------|---------------|---------------|-------------------------------------|
| `HAS_NAME`                 | `:Drug`       | `:DrugName`   | `source`, `created_at`              |
| `EQUIVALENT_TO`            | `:Drug`       | `:Drug`       | `confidence`, `source`, `created_at`|
| `TREATS`                   | `:Drug`       | `:Condition`  | `evidence_level`, `source`          |
| `CONTRAINDICATED_FOR`      | `:Drug`       | `:Condition`  | `severity`, `source`                |
| `CONTAINS_INGREDIENT`      | `:Drug`       | `:Ingredient` | `role` (active/inactive), `source`  |
| `INTERACTS_WITH`           | `:Drug`       | `:Drug`       | `severity`, `description`, `source` |
| `PARENT_OF`                | `:Condition`  | `:Condition`  | `source` (ICD-11/SNOMED hierarchy)  |
| `SOURCED_FROM`             | `:Drug`       | `:DataSource` | `ingested_at`                       |
| `SOURCED_FROM`             | `:Condition`  | `:DataSource` | `ingested_at`                       |

---

## Codex-Specific Design Decisions

### 1. Source Provenance (per task requirement)
Every node carries:
- `source` — which system the record came from
- `source_id` — the original primary key in that system
- `source_attribute_name` — the original field/attribute name in that system's schema

This allows tracing any Codex record back to its upstream origin.

### 2. Timestamps (per task requirement)
- `created_at` — set once at first ingestion
- `updated_at` — updated on every refresh cycle

### 3. POC Flag (per task requirement)
- `is_poc: true` on nodes that should be in the small development/demo/debug subset
- Allows running queries against POC-only data: `WHERE n.is_poc = true`

### 4. Drug Name Translation (core Codex purpose)
- `:Drug` → `HAS_NAME` → `:DrugName` with `country` and `language` properties
- Query pattern: find all names for the same drug across countries
- `EQUIVALENT_TO` relationship links drugs that are the same compound under different names

### 5. Future Sources
The schema is source-agnostic by design:
- New sources add their own `source` value to existing node types
- New node types can be added without breaking existing queries
- `:DataSource` nodes track all registered sources

---

## Example Query: Translate a Medicine Name

```cypher
// Given "Tylenol" (US), find equivalent names in India
MATCH (d:Drug)-[:HAS_NAME]->(n:DrugName {name: "Tylenol", country: "US"})
MATCH (d)-[:HAS_NAME]->(translated:DrugName {country: "IN"})
RETURN d.canonical_name AS drug, translated.name AS india_name, translated.language AS language
```

## Example Query: Find POC Subset

```cypher
MATCH (d:Drug {is_poc: true})-[:HAS_NAME]->(n:DrugName)
RETURN d.canonical_name, collect(n.name + " (" + n.country + ")") AS names
ORDER BY d.canonical_name
```
