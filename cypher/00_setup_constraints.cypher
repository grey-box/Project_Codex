// =============================================================
// Project Codex — Neo4j Schema Setup
// Step 0: Constraints and Indexes
// Run this FIRST before any data import
// =============================================================

// ---- Uniqueness Constraints ----

CREATE CONSTRAINT drug_codex_id IF NOT EXISTS
FOR (d:Drug) REQUIRE d.codex_id IS UNIQUE;

CREATE CONSTRAINT drugname_unique IF NOT EXISTS
FOR (dn:DrugName) REQUIRE (dn.name, dn.country, dn.language) IS UNIQUE;

CREATE CONSTRAINT condition_codex_id IF NOT EXISTS
FOR (c:Condition) REQUIRE c.codex_id IS UNIQUE;

CREATE CONSTRAINT ingredient_codex_id IF NOT EXISTS
FOR (i:Ingredient) REQUIRE i.codex_id IS UNIQUE;

CREATE CONSTRAINT datasource_name IF NOT EXISTS
FOR (ds:DataSource) REQUIRE ds.name IS UNIQUE;

// ---- Indexes for fast lookups ----

CREATE INDEX drug_source_id IF NOT EXISTS
FOR (d:Drug) ON (d.source_id);

CREATE INDEX drug_source IF NOT EXISTS
FOR (d:Drug) ON (d.source);

CREATE INDEX drug_canonical_name IF NOT EXISTS
FOR (d:Drug) ON (d.canonical_name);

CREATE INDEX drug_poc IF NOT EXISTS
FOR (d:Drug) ON (d.is_poc);

CREATE INDEX drugname_country IF NOT EXISTS
FOR (dn:DrugName) ON (dn.country);

CREATE INDEX drugname_language IF NOT EXISTS
FOR (dn:DrugName) ON (dn.language);

CREATE INDEX condition_icd11 IF NOT EXISTS
FOR (c:Condition) ON (c.icd11_code);

CREATE INDEX condition_snomed IF NOT EXISTS
FOR (c:Condition) ON (c.snomed_id);

CREATE INDEX ingredient_inchikey IF NOT EXISTS
FOR (i:Ingredient) ON (i.inchikey);

// ---- Register known data sources ----

MERGE (ds:DataSource {name: 'drugbank'})
SET ds.url = 'https://go.drugbank.com/',
    ds.license = 'Creative Commons Attribution-NonCommercial 4.0',
    ds.version = '5.1.10',
    ds.last_refreshed = datetime('2024-01-15T00:00:00Z');

MERGE (ds:DataSource {name: 'rxnorm'})
SET ds.url = 'https://www.nlm.nih.gov/research/umls/rxnorm/',
    ds.license = 'Public Domain (NLM)',
    ds.version = '2024-01-02',
    ds.last_refreshed = datetime('2024-01-10T00:00:00Z');

MERGE (ds:DataSource {name: 'icd11'})
SET ds.url = 'https://icd.who.int/en',
    ds.license = 'Creative Commons Attribution-NoDerivatives 3.0 IGO',
    ds.version = '2024-01',
    ds.last_refreshed = datetime('2024-01-08T00:00:00Z');

MERGE (ds:DataSource {name: 'snomedct'})
SET ds.url = 'https://www.snomed.org/',
    ds.license = 'SNOMED CT License',
    ds.version = '2023-09-01',
    ds.last_refreshed = datetime('2024-01-12T00:00:00Z');
