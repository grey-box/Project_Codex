// =============================================================
// Project Codex — DrugBank Source Loader
// Step 1: Load DrugBank data into normalized Codex schema
// Assumes: sample_data/drugbank_sample.json accessible via LOAD CSV
//          or data passed as parameters from Python ETL
// =============================================================

// ---- Create Drug nodes from DrugBank ----
// Note: In production, this runs per-record from the ETL pipeline.
//       Below is the idiomatic Cypher using MERGE for upsert semantics.

// Acetaminophen (Tylenol / Dolo / Panadol)
MERGE (d:Drug {source: 'drugbank', source_id: 'DB00316'})
ON CREATE SET
    d.codex_id            = 'codex-drug-' + 'DB00316',
    d.canonical_name      = 'Acetaminophen',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'drugbank_id',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET
    d.updated_at          = datetime();

// DrugName nodes for Acetaminophen
MERGE (dn:DrugName {name: 'Acetaminophen', country: 'US', language: 'en'})
ON CREATE SET dn.name_type = 'generic', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Tylenol', country: 'US', language: 'en'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = false,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Panadol', country: 'GB', language: 'en'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Dolo', country: 'IN', language: 'hi'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Dafalgan', country: 'FR', language: 'fr'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Ben-u-ron', country: 'DE', language: 'de'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

// Connect Drug → DrugNames
MATCH (d:Drug {source_id: 'DB00316'})
MATCH (dn:DrugName) WHERE dn.name IN ['Acetaminophen','Tylenol','Panadol','Dolo','Dafalgan','Ben-u-ron']
MERGE (d)-[:HAS_NAME {source: 'drugbank', created_at: datetime()}]->(dn);

// Connect Drug → DataSource
MATCH (d:Drug {source_id: 'DB00316'}), (ds:DataSource {name: 'drugbank'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// Ingredient node for Acetaminophen
MERGE (i:Ingredient {source: 'drugbank', source_id: 'DB00316-active'})
ON CREATE SET
    i.codex_id            = 'codex-ing-APAP',
    i.name                = 'Acetaminophen',
    i.cas_number          = '103-90-2',
    i.inchikey            = 'RZVAJINKPMORJF-UHFFFAOYSA-N',
    i.source_attribute_name = 'cas_number',
    i.created_at          = datetime(),
    i.updated_at          = datetime(),
    i.is_poc              = true;

MATCH (d:Drug {source_id: 'DB00316'}), (i:Ingredient {source_id: 'DB00316-active'})
MERGE (d)-[:CONTAINS_INGREDIENT {role: 'active', source: 'drugbank'}]->(i);

// ---- Aspirin ----
MERGE (d:Drug {source: 'drugbank', source_id: 'DB00945'})
ON CREATE SET
    d.codex_id            = 'codex-drug-DB00945',
    d.canonical_name      = 'Aspirin',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'drugbank_id',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

MERGE (dn:DrugName {name: 'Aspirin', country: 'US', language: 'en'})
ON CREATE SET dn.name_type = 'generic', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Disprin', country: 'IN', language: 'hi'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Aspro', country: 'AU', language: 'en'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MATCH (d:Drug {source_id: 'DB00945'})
MATCH (dn:DrugName) WHERE dn.name IN ['Aspirin','Disprin','Aspro']
MERGE (d)-[:HAS_NAME {source: 'drugbank', created_at: datetime()}]->(dn);

MATCH (d:Drug {source_id: 'DB00945'}), (ds:DataSource {name: 'drugbank'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// ---- Metformin ----
MERGE (d:Drug {source: 'drugbank', source_id: 'DB00331'})
ON CREATE SET
    d.codex_id            = 'codex-drug-DB00331',
    d.canonical_name      = 'Metformin',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'drugbank_id',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

MERGE (dn:DrugName {name: 'Glucophage', country: 'US', language: 'en'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Glycomet', country: 'IN', language: 'hi'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Metforal', country: 'IT', language: 'it'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Siofor', country: 'DE', language: 'de'})
ON CREATE SET dn.name_type = 'brand', dn.is_primary = true,
              dn.source = 'drugbank', dn.source_attribute_name = 'brands.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MATCH (d:Drug {source_id: 'DB00331'})
MATCH (dn:DrugName) WHERE dn.name IN ['Glucophage','Glycomet','Metforal','Siofor']
MERGE (d)-[:HAS_NAME {source: 'drugbank', created_at: datetime()}]->(dn);

MATCH (d:Drug {source_id: 'DB00331'}), (ds:DataSource {name: 'drugbank'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// ---- Drug Interactions ----
MATCH (d1:Drug {source_id: 'DB00316'}), (d2:Drug {source_id: 'DB00682'})
MERGE (d1)-[:INTERACTS_WITH {
    severity: 'moderate',
    description: 'Warfarin anticoagulant effect may be increased',
    source: 'drugbank'
}]->(d2);
