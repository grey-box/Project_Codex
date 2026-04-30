# Codex Medical Translation API

The **Codex Medical Translation API v3.0** is a FastAPI service designed to translate drug and medical terms across languages and countries using a Neo4j-backed graph database.

It acts as a thin HTTP layer over the Codex core services, handling request validation, routing, and standardized responses.

---

## Base URL
`http://localhost:8000`

---

## Overview

This API provides:

- **Drug Translation** between source and target languages
- **Search** across all stored terms (case-insensitive, partial match)
- **Full Data Access** via CSV-style endpoints
- **Source Tracking** for imported datasets
- **Country/Language Metadata**
- **Bulk Data Upload** via CSV ingestion
- **Database Management** (reset, shutdown)

---

## Data Model Summary

Each term is represented as a row with:

| Field         | Description |
|--------------|------------|
| source_id     | Identifier from original dataset |
| source_name   | Dataset/source name |
| name          | Drug/term name |
| type          | Term type (e.g., canonical, brand) |
| country       | ISO country code |
| language      | Language code or name |
| uploaded_at   | Timestamp of ingestion |

---

## Endpoints

---

### 1. Health Check

Checks API status and Neo4j connectivity.

- **Method:** `GET`
- **Path:** `/health`

#### Response
```json
{
  "status": "ok",
  "neo4j": true,
  "api_version": "3.0.0"
}
```

---

### 2. Translate a Term

Translate a drug name from one language to another.

- **Method:** `POST`
- **Path:** `/translate`

#### Request Body
```json
{
  "term": "Ibuprofen",
  "source_lang": "en",
  "target_lang": "es",
  "target_country": "MX",
  "source_name": null
}
```

| Parameter       | Type   | Required | Description |
|----------------|--------|----------|-------------|
| term            | string | Yes      | Input drug name |
| source_lang     | string | Yes      | Source language |
| target_lang     | string | Yes      | Target language |
| target_country  | string | No       | Filter by country |
| source_name     | string | No       | Filter by dataset/source |

#### Response
```json
{
  "term": "Ibuprofen",
  "source_lang": "en",
  "target_lang": "es",
  "target_country": "MX",
  "source_name": null,
  "found": true,
  "results": [
    {
      "source_id": "123",
      "source_name": "FDA",
      "name": "ibuprofeno",
      "type": "generic",
      "country": "MX",
      "language": "es",
      "uploaded_at": "2026-04-30T12:00:00Z"
    }
  ]
}
```

---

### 3. Search Terms

Search for terms using partial, case-insensitive matching.

- **Method:** `POST`
- **Path:** `/search`

#### Request Body
```json
{
  "query": "aspirin",
  "limit": 10
}
```

#### Response
```json
{
  "query": "aspirin",
  "count": 2,
  "results": [
    {
      "source_id": "1",
      "source_name": "WHO",
      "name": "aspirin",
      "type": "canonical",
      "country": "US",
      "language": "en",
      "uploaded_at": "2026-04-30T12:00:00Z"
    }
  ]
}
```

---

## Data Retrieval (CSV-style Endpoints)

---

### 4. Get All Terms

- **Method:** `GET`
- **Path:** `/csv`

Returns all terms in the database.

---

### 5. Get Terms by Concept ID

- **Method:** `GET`
- **Path:** `/csv/concept/{concept_id}`

Returns all terms linked to a concept.

---

### 6. Get Terms by Country

- **Method:** `GET`
- **Path:** `/csv/country/{country}`

Returns all terms for a specific country.

---

### 7. Get Terms by Language

- **Method:** `GET`
- **Path:** `/csv/language/{language}`

Returns all terms for a given language.

---

### Generic Response Format
```json
{
  "generated_at": "2026-04-30T12:00:00Z",
  "row_count": 100,
  "rows": [
    {
      "source_id": "123",
      "source_name": "FDA",
      "name": "Ibuprofen",
      "type": "generic",
      "country": "US",
      "language": "en",
      "uploaded_at": "2026-04-30T12:00:00Z"
    }
  ]
}
```

---

## Sources

---

### 8. List Sources

- **Method:** `GET`
- **Path:** `/sources`

#### Response
```json
{
  "sources": [
    {
      "source_name": "FDA",
      "term_count": 1200,
      "last_uploaded": "2026-04-30T12:00:00Z"
    }
  ]
}
```

---

### 9. Get Terms by Source

- **Method:** `GET`
- **Path:** `/sources/{source_name}`

Returns all terms from a specific dataset.

---

## Metadata

---

### 10. List Countries

- **Method:** `GET`
- **Path:** `/countries`

#### Response
```json
{
  "countries": [
    {
      "country": "US",
      "languages": ["en"]
    }
  ]
}
```

---

### 11. List Languages

- **Method:** `GET`
- **Path:** `/languages`

#### Response
```json
{
  "languages": ["en", "es", "fr"]
}
```

---

## Data Management

---

### 12. Upload CSV

Upload a dataset into the system.

- **Method:** `POST`
- **Path:** `/csv/upload`
- **Content-Type:** `multipart/form-data`

#### Expected CSV Columns
```
Concept ID, Source ID, Source Name, Name, Type, Country, Language
```

- `Concept ID` is optional (auto-generated if missing)

#### Response
```json
{
  "generated_at": "2026-04-30T12:00:00Z",
  "row_count": 500,
  "filename": "drugs.csv",
  "message": "Imported 500 entries from drugs.csv"
}
```

---

### 13. Reset Database

Deletes all data.

- **Method:** `POST`
- **Path:** `/reset`

#### Response
```json
{
  "status": "ok",
  "message": "Database wiped successfully"
}
```

---

### 14. Shutdown API

Gracefully shuts down the server.

- **Method:** `POST`
- **Path:** `/shutdown`

#### Response
```json
{
  "status": "shutting_down"
}
```

---

## Error Handling

| Code | Meaning |
|------|--------|
| 200  | Success |
| 201  | Resource Created |
| 400  | Bad Request |
| 404  | Not Found |
| 500  | Internal Server Error |

---

## Notes

- All timestamps are in **UTC ISO 8601 format**
- Searches are **case-insensitive and partial-match**
- CSV ingestion is the **primary method of loading data**
- Translation operates via **shared Concept IDs in Neo4j**

---
