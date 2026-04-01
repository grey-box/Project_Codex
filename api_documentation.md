# Codex Medical Translation API

The **Codex Medical Translation API** is a FastAPI service designed to translate drug names across different languages and countries using a Neo4j-backed graph database. 

It serves as a thin HTTP layer over a core translation engine, managing request validation, routing, and standardized response formatting.

---

## Base URL
`http://localhost:8000`

## Overview
This API provides a robust framework for:
* **Translation** of medical terms across specific languages and regions.
* **Resolution** of brand names to their canonical drug counterparts.
* **Fallback handling** logic for missing translations.
* **Auditing** coverage of translations and brand names globally.
* **Data Management** via structured language pack uploads to Neo4j.

## Data Model Summary
The API utilizes a graph-based structure consisting of:
* **Canonical Terms:** The base scientific name (e.g., *ibuprofen*).
* **Translations:** Language and country-specific nodes.
* **Brand Names:** Commercial names linked to regional equivalents.
* **Language Nodes:** Representing available datasets.

---

## Endpoints

### 1. Health Check
Checks the API status and connectivity to the Neo4j database.

* **Method:** `GET`
* **Path:** `/health`

### Response
```json
{
  "status": "ok",
  "neo4j": true,
  "api_version": "1.0.0"
}
```

### 2. Translate a Term
Translates a medical term into a target language and optionally filters by country.

* **Method:** 'POST'

* **Path:** '/translate'

### Request Body
```JSON
{
  "term": "ibuprofen",
  "lang": "es",
  "country": "MX"
}
```

| Parameter | Type   | Required | Description                                    |
| --------- | ------ | -------- | ---------------------------------------------- |
| term      | string | Yes      | Input term (canonical, brand, or fuzzy match). |
| lang      | string | No       | Target ISO language code (e.g., "es").         |
| country   | string | No       | Target ISO country code (e.g., "MX").          |


### Response
```JSON
{
  "canonical": "ibuprofen",
  "requested_language": "es",
  "used_language": "es",
  "fallback_used": false,
  "fallback_type": null,
  "fallback_chain": null,
  "missing_language_pack": false,
  "results": [
    {
      "translation": "ibuprofeno",
      "language": "Spanish",
      "brand": "Advil",
      "country": "MX"
    }
  ]
}
```

### 3. Audit a Term
Provides a coverage analysis for a specific term to identify missing data points.

* **Method:** GET

* **Path:**/audit/{term}

Example
GET /audit/ibuprofen

### Response
```JSON
{
  "term": "ibuprofen",
  "canonical": "ibuprofen",
  "missing_translations": [
    { "country": "NG", "country_name": "Nigeria" }
  ],
  "missing_brands": [
    { "country": "FR", "country_name": "France" }
  ],
  "equivalent_brands": [
    { "brand": "Advil", "country": "US", "country_name": "United States" }
  ]
}
```

### 4. Load Demo Data
Loads a predefined dataset (Ibuprofen, Paracetamol, Amoxicillin) into Neo4j for testing.

* **Method:** POST

* **Path:**/demo/load

### 5. Upload Language Pack
Uploads and processes a JSON language pack into the database.

* **Method:** POST

* **Path:**/packs/load

Content-Type: multipart/form-data

Expected JSON File Format
```JSON
{
  "language": { "code": "pt", "name": "Portuguese" },
  "terms": [
    {
      "canonical": "Ibuprofen",
      "entries": [
        {
          "translation": "ibuprofeno",
          "country": "BR",
          "brand": "Advil"
        }
      ]
    }
  ]
}
```

### 6. List Available Languages
Returns a list of all language codes currently stored in the system.

* **Method:** GET

* **Path:**/languages

#### Error Handling
The API uses standard HTTP status codes.

| Code    | Meaning                          |
| ------- | -------------------------------- |
| 200/201 | Success / Resource Created       |
| 400     | Bad Request (Invalid input/file) |
| 404     | Not Found                        |
| 500     | Internal Server Error            |

