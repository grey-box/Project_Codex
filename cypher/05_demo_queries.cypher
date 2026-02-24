// =============================================================
// Project Codex — Demo Queries
// Showcase the value of the normalized schema
// =============================================================

// ---- Query 1: Core Codex Use Case — Translate a medicine name ----
// "What is Tylenol called in India, France, and Germany?"

MATCH (d:Drug)-[:HAS_NAME]->(us_name:DrugName {name: 'Tylenol', country: 'US'})
MATCH (d)-[:HAS_NAME]->(intl:DrugName)
WHERE intl.country <> 'US'
RETURN d.canonical_name AS drug,
       intl.name        AS international_name,
       intl.country     AS country,
       intl.language    AS language,
       intl.name_type   AS type
ORDER BY intl.country;


// ---- Query 2: Find all names for the same compound across all sources ----
// "Show me everything we know about Acetaminophen/Paracetamol"

MATCH (d:Drug)
WHERE d.canonical_name IN ['Acetaminophen', 'Paracetamol']
   OR d.source_id IN ['DB00316', '387517004', '161']
OPTIONAL MATCH (d)-[:HAS_NAME]->(dn:DrugName)
OPTIONAL MATCH (d)-[:EQUIVALENT_TO]->(eq:Drug)
RETURN d.source         AS source,
       d.source_id      AS source_id,
       d.canonical_name AS canonical_name,
       collect(DISTINCT dn.name + ' (' + dn.country + ')') AS names,
       collect(DISTINCT eq.canonical_name + ' [' + eq.source + ']') AS equivalents;


// ---- Query 3: POC subset — all drugs with their translation names ----

MATCH (d:Drug {is_poc: true})-[:HAS_NAME]->(n:DrugName {is_poc: true})
RETURN d.canonical_name AS drug,
       d.source         AS source,
       collect(n.name + ' (' + n.country + ', ' + n.language + ')') AS names
ORDER BY d.canonical_name;


// ---- Query 4: Drug-Condition treatment graph ----

MATCH (d:Drug)-[t:TREATS]->(c:Condition)
RETURN d.canonical_name  AS drug,
       d.source          AS drug_source,
       c.canonical_name  AS condition,
       c.icd11_code      AS icd11_code,
       t.evidence_level  AS evidence
ORDER BY d.canonical_name;


// ---- Query 5: Drug interaction safety check ----

MATCH (d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)
RETURN d1.canonical_name AS drug_1,
       d2.canonical_name AS drug_2,
       i.severity        AS severity,
       i.description     AS description;


// ---- Query 6: Provenance — where did this data come from? ----

MATCH (d:Drug)-[:SOURCED_FROM]->(ds:DataSource)
RETURN d.canonical_name    AS drug,
       d.source            AS source_system,
       d.source_id         AS original_id,
       d.source_attribute_name AS original_field,
       ds.version          AS source_version,
       ds.last_refreshed   AS last_refreshed,
       d.created_at        AS ingested_at
ORDER BY d.canonical_name, d.source;


// ---- Query 7: Cross-source equivalence map ----
// Show the full graph of equivalent drugs across all sources

MATCH (d1:Drug)-[:EQUIVALENT_TO]->(d2:Drug)
RETURN d1.canonical_name AS name_a,
       d1.source         AS source_a,
       d1.source_id      AS id_a,
       d2.canonical_name AS name_b,
       d2.source         AS source_b,
       d2.source_id      AS id_b;


// ---- Query 8: Data freshness audit ----

MATCH (ds:DataSource)
RETURN ds.name           AS source,
       ds.version        AS version,
       ds.last_refreshed AS last_refreshed,
       ds.license        AS license
ORDER BY ds.name;


// ---- Query 9: Find all brand names for a generic drug across countries ----
// Given a generic INN name, show all brand names worldwide

MATCH (d:Drug {canonical_name: 'Metformin', source: 'drugbank'})
MATCH (d)-[:HAS_NAME]->(n:DrugName {name_type: 'brand'})
RETURN n.name    AS brand_name,
       n.country AS country,
       n.language AS language
ORDER BY n.country;


// ---- Query 10: Count records by source and POC flag ----

MATCH (d:Drug)
RETURN d.source   AS source,
       d.is_poc   AS is_poc,
       count(d)   AS drug_count
ORDER BY d.source, d.is_poc;
