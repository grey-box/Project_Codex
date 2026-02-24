// =============================================================
// Project Codex — SNOMED CT Source Loader
// Step 4: Load SNOMED CT concepts and link to existing nodes
// =============================================================

// ---- Paracetamol (SNOMED 387517004) — same as Acetaminophen ----
// SNOMED uses "Paracetamol" (INN/WHO name) vs US "Acetaminophen"
// This demonstrates the core Codex translation use case

MERGE (d:Drug {source: 'snomedct', source_id: '387517004'})
ON CREATE SET
    d.codex_id            = 'codex-drug-SCT387517004',
    d.canonical_name      = 'Paracetamol',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'concept_id',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

MATCH (d:Drug {source: 'snomedct', source_id: '387517004'}), (ds:DataSource {name: 'snomedct'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// SNOMED synonyms for Paracetamol
MERGE (dn:DrugName {name: 'Paracetamol', country: 'GB', language: 'en'})
ON CREATE SET dn.name_type = 'generic', dn.is_primary = true,
              dn.source = 'snomedct', dn.source_attribute_name = 'descriptions.FSN',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Paracetamol', country: 'IN', language: 'en'})
ON CREATE SET dn.name_type = 'generic', dn.is_primary = false,
              dn.source = 'snomedct', dn.source_attribute_name = 'descriptions.Synonym',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MERGE (dn:DrugName {name: 'Paracetamol', country: 'AU', language: 'en'})
ON CREATE SET dn.name_type = 'generic', dn.is_primary = true,
              dn.source = 'snomedct', dn.source_attribute_name = 'descriptions.Synonym',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = true;

MATCH (d:Drug {source: 'snomedct', source_id: '387517004'})
MATCH (dn:DrugName) WHERE dn.name = 'Paracetamol'
MERGE (d)-[:HAS_NAME {source: 'snomedct', created_at: datetime()}]->(dn);

// Critical: EQUIVALENT_TO between DrugBank Acetaminophen and SNOMED Paracetamol
MATCH (db:Drug {source: 'drugbank', source_id: 'DB00316'})
MATCH (sct:Drug {source: 'snomedct', source_id: '387517004'})
MERGE (db)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'inchikey',
    note: 'Same compound, different regional names',
    created_at: datetime()
}]->(sct);

// ---- Aspirin (SNOMED 387458008) ----
MERGE (d:Drug {source: 'snomedct', source_id: '387458008'})
ON CREATE SET
    d.codex_id            = 'codex-drug-SCT387458008',
    d.canonical_name      = 'Aspirin',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'concept_id',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

MATCH (d:Drug {source: 'snomedct', source_id: '387458008'}), (ds:DataSource {name: 'snomedct'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

MATCH (db:Drug {source: 'drugbank', source_id: 'DB00945'})
MATCH (sct:Drug {source: 'snomedct', source_id: '387458008'})
MERGE (db)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'name+inchikey',
    created_at: datetime()
}]->(sct);

// ---- Metformin (SNOMED 387467008) ----
MERGE (d:Drug {source: 'snomedct', source_id: '387467008'})
ON CREATE SET
    d.codex_id            = 'codex-drug-SCT387467008',
    d.canonical_name      = 'Metformin',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'concept_id',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

MATCH (d:Drug {source: 'snomedct', source_id: '387467008'}), (ds:DataSource {name: 'snomedct'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

MATCH (db:Drug {source: 'drugbank', source_id: 'DB00331'})
MATCH (sct:Drug {source: 'snomedct', source_id: '387467008'})
MERGE (db)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'name+inchikey',
    created_at: datetime()
}]->(sct);

// ---- SNOMED Condition: Type 2 Diabetes (44508008) ----
MERGE (c:Condition {source: 'snomedct', source_id: '44508008'})
ON CREATE SET
    c.codex_id            = 'codex-cond-SCT44508008',
    c.canonical_name      = 'Type 2 diabetes mellitus',
    c.snomed_id           = '44508008',
    c.source_attribute_name = 'concept_id',
    c.created_at          = datetime(),
    c.updated_at          = datetime(),
    c.is_poc              = true
ON MATCH SET c.updated_at = datetime();

MATCH (c:Condition {source: 'snomedct', source_id: '44508008'}), (ds:DataSource {name: 'snomedct'})
MERGE (c)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// Link SNOMED condition to ICD-11 condition (same disorder)
MATCH (icd:Condition {source: 'icd11', source_id: 'JA00'})
MATCH (sct:Condition {source: 'snomedct', source_id: '44508008'})
MERGE (icd)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'clinical-mapping',
    created_at: datetime()
}]->(sct);

// Enrich ICD-11 condition with SNOMED ID
MATCH (c:Condition {source: 'icd11', source_id: 'JA00'})
SET c.snomed_id = '44508008';

// ---- SNOMED Condition: Rheumatoid Arthritis (69896004) ----
MERGE (c:Condition {source: 'snomedct', source_id: '69896004'})
ON CREATE SET
    c.codex_id            = 'codex-cond-SCT69896004',
    c.canonical_name      = 'Rheumatoid arthritis',
    c.snomed_id           = '69896004',
    c.source_attribute_name = 'concept_id',
    c.created_at          = datetime(),
    c.updated_at          = datetime(),
    c.is_poc              = true
ON MATCH SET c.updated_at = datetime();

MATCH (c:Condition {source: 'snomedct', source_id: '69896004'}), (ds:DataSource {name: 'snomedct'})
MERGE (c)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

MATCH (icd:Condition {source: 'icd11', source_id: 'FA24'})
MATCH (sct:Condition {source: 'snomedct', source_id: '69896004'})
MERGE (icd)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'clinical-mapping',
    created_at: datetime()
}]->(sct);

MATCH (c:Condition {source: 'icd11', source_id: 'FA24'})
SET c.snomed_id = '69896004';
