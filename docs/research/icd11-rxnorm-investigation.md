# ICD-11 and RxNorm Database Investigation

Date: November 12, 2026
Branch: feature/icd11-merge-rxnorm

## Objective

Investigate ICD-11 ingestion and determine how ICD-11
and RxNorm records could be queried together for the
Project Codex CSV export functionality.

## Existing Database

Verified the existing Neo4j database contained:

- 62,291 RxNorm nodes
- 62,290 Concept nodes (overlapping labels)
- 99 Translation nodes
- 47 Brand nodes
- 11 Term nodes

ICD-11 initially had zero nodes.

## ICD-11 Ingestion

Reviewed the ICD-11 ingestion function in source_data.py.

- Imported through POST /api/populate-sources
- Source selection: icd11
- Requires WHO ICD API client credentials
- Uses ICD-11 release 2024-01 by default
- Imports Chapter 21
- Creates ICD nodes and HAS_CHILD relationships

Initial requests without WHO credentials were skipped.
After obtaining credentials, ingestion began successfully.

During ingestion, verified:
- 290 ICD nodes
- 289 ICD HAS_CHILD relationships
- Dataset: ICD11-21:2024-01

These were intermediate counts, not final import totals.

## ICD-11 Node Schema

Observed properties:

- id: WHO ICD-11 concept identifier
- code: ICD classification code, sometimes absent
- title: clinical concept name
- ds: dataset identifier

Query:

MATCH (n:ICD)
RETURN n.id, n.code, n.title, n.ds
LIMIT 10;

## Combined Dataset Query

Tested retrieving both datasets in a common format.

CALL {
    MATCH (n:RXN)
    RETURN
        'RxNorm' AS source,
        n.conceptID AS concept_id,
        n.name AS name,
        n.rxcui AS code,
        n.tty AS concept_type
    ORDER BY n.name
    LIMIT 5

    UNION ALL

    MATCH (n:ICD)
    RETURN
        'ICD-11' AS source,
        n.id AS concept_id,
        n.title AS name,
        n.code AS code,
        'ICD-11' AS concept_type
    ORDER BY n.title
    LIMIT 5
}
RETURN source, concept_id, name, code, concept_type
ORDER BY source, name;

Result: Successfully retrieved five records from each
dataset with consistent output columns.

## Findings

RxNorm contains medication terminology, while ICD-11
Chapter 21 contains symptoms, signs, and clinical findings.

Although the datasets can be returned by one Cypher query,
including ICD-11 in a medication-only CSV may not be
appropriate.

ICD-11 codes are sometimes missing, so exports must
support nullable classification codes.

## Outstanding Work

- Verify final ICD-11 ingestion status and counts.
- Confirm export requirements with the sponsor.
- Bring existing RxNorm CSV functionality into this branch.
- Implement backend queries once export scope is confirmed.
- Add automated tests for combined query results.

## Notes

No API credentials or authentication tokens are stored
in this document.
