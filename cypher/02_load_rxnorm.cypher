// =============================================================
// Project Codex — RxNorm Source Loader
// Step 2: Map RxNorm concepts into the normalized Codex schema
// RxNorm is US-centric; maps to existing Drug nodes via InChIKey / name match
// =============================================================

// RxNorm uses MERGE ON MATCH to enrich existing Drug nodes with RxCUI,
// or creates new Drug nodes if the drug isn't in DrugBank yet.

// ---- Acetaminophen (RxCUI 161) ----
// Already in graph from DrugBank; enrich with RxNorm IDs
MERGE (d:Drug {source: 'rxnorm', source_id: '161'})
ON CREATE SET
    d.codex_id            = 'codex-drug-RX161',
    d.canonical_name      = 'Acetaminophen',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'rxcui',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

// Link RxNorm entry to DataSource
MATCH (d:Drug {source: 'rxnorm', source_id: '161'}), (ds:DataSource {name: 'rxnorm'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// Establish EQUIVALENT_TO between DrugBank and RxNorm representations
MATCH (db:Drug {source: 'drugbank', source_id: 'DB00316'})
MATCH (rx:Drug {source: 'rxnorm', source_id: '161'})
MERGE (db)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'name+inchikey',
    created_at: datetime()
}]->(rx);

// Add RxNorm-specific name variants (clinical dose forms)
MERGE (dn:DrugName {name: 'Acetaminophen 325 MG Oral Tablet', country: 'US', language: 'en'})
ON CREATE SET dn.name_type = 'clinical_dose_form', dn.is_primary = false,
              dn.source = 'rxnorm', dn.source_attribute_name = 'SCD.name',
              dn.created_at = datetime(), dn.updated_at = datetime(), dn.is_poc = false;

MATCH (d:Drug {source: 'rxnorm', source_id: '161'})
MATCH (dn:DrugName {name: 'Acetaminophen 325 MG Oral Tablet', country: 'US', language: 'en'})
MERGE (d)-[:HAS_NAME {source: 'rxnorm', created_at: datetime()}]->(dn);

// ---- Aspirin (RxCUI 1191) ----
MERGE (d:Drug {source: 'rxnorm', source_id: '1191'})
ON CREATE SET
    d.codex_id            = 'codex-drug-RX1191',
    d.canonical_name      = 'Aspirin',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'rxcui',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

MATCH (d:Drug {source: 'rxnorm', source_id: '1191'}), (ds:DataSource {name: 'rxnorm'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

MATCH (db:Drug {source: 'drugbank', source_id: 'DB00945'})
MATCH (rx:Drug {source: 'rxnorm', source_id: '1191'})
MERGE (db)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'name+inchikey',
    created_at: datetime()
}]->(rx);

// ---- Metformin (RxCUI 6809) ----
MERGE (d:Drug {source: 'rxnorm', source_id: '6809'})
ON CREATE SET
    d.codex_id            = 'codex-drug-RX6809',
    d.canonical_name      = 'Metformin',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'rxcui',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = true
ON MATCH SET d.updated_at = datetime();

MATCH (d:Drug {source: 'rxnorm', source_id: '6809'}), (ds:DataSource {name: 'rxnorm'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

MATCH (db:Drug {source: 'drugbank', source_id: 'DB00331'})
MATCH (rx:Drug {source: 'rxnorm', source_id: '6809'})
MERGE (db)-[:EQUIVALENT_TO {
    confidence: 1.0,
    source: 'codex-normalization',
    match_basis: 'name+inchikey',
    created_at: datetime()
}]->(rx);

// ---- Warfarin (RxCUI 11289) ----
MERGE (d:Drug {source: 'rxnorm', source_id: '11289'})
ON CREATE SET
    d.codex_id            = 'codex-drug-RX11289',
    d.canonical_name      = 'Warfarin',
    d.drug_type           = 'small_molecule',
    d.is_approved         = true,
    d.source_attribute_name = 'rxcui',
    d.created_at          = datetime(),
    d.updated_at          = datetime(),
    d.is_poc              = false
ON MATCH SET d.updated_at = datetime();

MATCH (d:Drug {source: 'rxnorm', source_id: '11289'}), (ds:DataSource {name: 'rxnorm'})
MERGE (d)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);
