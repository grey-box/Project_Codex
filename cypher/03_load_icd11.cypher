// =============================================================
// Project Codex — ICD-11 Source Loader
// Step 3: Load ICD-11 conditions into the normalized Codex schema
// =============================================================

// ---- Type 2 Diabetes Mellitus (JA00) ----
MERGE (c:Condition {source: 'icd11', source_id: 'JA00'})
ON CREATE SET
    c.codex_id            = 'codex-cond-ICD-JA00',
    c.canonical_name      = 'Type 2 diabetes mellitus',
    c.icd11_code          = 'JA00',
    c.source_attribute_name = 'code',
    c.created_at          = datetime(),
    c.updated_at          = datetime(),
    c.is_poc              = true
ON MATCH SET c.updated_at = datetime();

MATCH (c:Condition {source_id: 'JA00'}), (ds:DataSource {name: 'icd11'})
MERGE (c)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// ---- Hypertensive diseases (BA00) ----
MERGE (c:Condition {source: 'icd11', source_id: 'BA00'})
ON CREATE SET
    c.codex_id            = 'codex-cond-ICD-BA00',
    c.canonical_name      = 'Hypertensive diseases',
    c.icd11_code          = 'BA00',
    c.source_attribute_name = 'code',
    c.created_at          = datetime(),
    c.updated_at          = datetime(),
    c.is_poc              = true
ON MATCH SET c.updated_at = datetime();

MATCH (c:Condition {source_id: 'BA00'}), (ds:DataSource {name: 'icd11'})
MERGE (c)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// ---- Atrial fibrillation (CA01) ----
MERGE (c:Condition {source: 'icd11', source_id: 'CA01'})
ON CREATE SET
    c.codex_id            = 'codex-cond-ICD-CA01',
    c.canonical_name      = 'Atrial fibrillation',
    c.icd11_code          = 'CA01',
    c.source_attribute_name = 'code',
    c.created_at          = datetime(),
    c.updated_at          = datetime(),
    c.is_poc              = false
ON MATCH SET c.updated_at = datetime();

MATCH (c:Condition {source_id: 'CA01'}), (ds:DataSource {name: 'icd11'})
MERGE (c)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// ---- Rheumatoid arthritis (FA24) ----
MERGE (c:Condition {source: 'icd11', source_id: 'FA24'})
ON CREATE SET
    c.codex_id            = 'codex-cond-ICD-FA24',
    c.canonical_name      = 'Rheumatoid arthritis',
    c.icd11_code          = 'FA24',
    c.source_attribute_name = 'code',
    c.created_at          = datetime(),
    c.updated_at          = datetime(),
    c.is_poc              = true
ON MATCH SET c.updated_at = datetime();

MATCH (c:Condition {source_id: 'FA24'}), (ds:DataSource {name: 'icd11'})
MERGE (c)-[:SOURCED_FROM {ingested_at: datetime()}]->(ds);

// ---- ICD-11 Chapter hierarchy (PARENT_OF) ----
// Hypertensive diseases is a parent of Atrial fibrillation (both circulatory)
MATCH (parent:Condition {source_id: 'BA00'})
MATCH (child:Condition {source_id: 'CA01'})
MERGE (parent)-[:PARENT_OF {source: 'icd11'}]->(child);

// ---- Drug → Condition TREATS relationships ----
// Metformin treats Type 2 diabetes
MATCH (d:Drug {source: 'drugbank', source_id: 'DB00331'})
MATCH (c:Condition {source_id: 'JA00'})
MERGE (d)-[:TREATS {
    evidence_level: 'A',
    source: 'drugbank+icd11',
    created_at: datetime()
}]->(c);

// Warfarin treats Atrial fibrillation
MATCH (d:Drug {source: 'drugbank', source_id: 'DB00682'})
MATCH (c:Condition {source_id: 'CA01'})
MERGE (d)-[:TREATS {
    evidence_level: 'A',
    source: 'drugbank+icd11',
    created_at: datetime()
}]->(c);

// Methotrexate treats Rheumatoid arthritis
MATCH (d:Drug {source: 'drugbank', source_id: 'DB00563'})
MATCH (c:Condition {source_id: 'FA24'})
MERGE (d)-[:TREATS {
    evidence_level: 'A',
    source: 'drugbank+icd11',
    created_at: datetime()
}]->(c);

// Aspirin contraindicated for certain bleeding conditions (example)
MATCH (d:Drug {source: 'drugbank', source_id: 'DB00945'})
MATCH (c:Condition {source_id: 'CA01'})
MERGE (d)-[:TREATS {
    evidence_level: 'B',
    source: 'drugbank+icd11',
    note: 'antiplatelet therapy for AF stroke prevention',
    created_at: datetime()
}]->(c);
