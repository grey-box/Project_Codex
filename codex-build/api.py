"""
Codex Translation API
FastAPI service that sits between the Frontend and the backend

All business logic lives in codex/.  This file only:
  - Defines request / response shapes (Pydantic models)
  - Routes HTTP calls to the right backend function
  - Formats errors consistently

Endpoints
---------
  GET  /health       Liveness check — API + Neo4j
  POST /translate    Translate a drug name from one language to another
  GET  /audit/{term} Quality audit (missing translations / brands)
  GET  /languages    List language codes that have data in Neo4j
  GET  /countries    List supported countries and their languages
  POST /csv/upload   Upload a Codex CSV → Neo4j
  GET  /csv          Export full drug catalogue as sorted JSON envelope
"""

from __future__ import annotations

import csv
import io
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    from codex.services.translation_service import translate
    from codex.neo4j_driver import (
        driver,
        find_missing_translations,
        find_missing_brands,
        get_equivalent_brands,
        resolve_to_base_term,
        import_csv_drugs,
        get_drugs_table,
        get_countries_languages,
    )
except Exception as exc:
    logging.critical("Failed to import codex backend: %s", exc)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("codex.api")

app = FastAPI(
    title="Codex Medical Translation API",
    description="Translate drug names across languages using Neo4j.",
    version="2.0.0",
)


#Pydantic models

class TranslateRequest(BaseModel):
    term: str
    source_lang: str
    target_lang: str
    country: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {
        "term": "Advil", "source_lang": "en", "target_lang": "es", "country": "MX",
    }}}


class TranslateResultRow(BaseModel):
    brand_name: Optional[str]
    generic_name: str
    original_language: str
    translated_language: str


class CsvEnvelopeMeta(BaseModel):
    generated_at: str
    row_count: int
    source: str
    sort_order: str = "generic_name_asc"


class TranslateResponse(BaseModel):
    metadata: CsvEnvelopeMeta
    term: str
    source_lang: str
    target_lang: str
    country: Optional[str]
    found: bool
    csv: list[TranslateResultRow]


class AuditEntry(BaseModel):
    country: str
    country_name: str
    reason: Optional[str] = None


class BrandEntry(BaseModel):
    brand: str
    country: str
    country_name: str


class AuditResponse(BaseModel):
    term: str
    canonical: str
    missing_translations: list[AuditEntry]
    missing_brands: list[AuditEntry]
    equivalent_brands: list[BrandEntry]


class LanguagesResponse(BaseModel):
    languages: list[str]


class HealthResponse(BaseModel):
    status: str
    neo4j: bool
    api_version: str


class DrugRow(BaseModel):
    generic_name: str
    brand_name: Optional[str]
    country: Optional[str]
    original_language: str
    translated_language: str


class CountryRow(BaseModel):
    iso_code: str
    languages: list[str]


class CsvUploadResponse(BaseModel):
    metadata: CsvEnvelopeMeta
    message: str


class CsvExportResponse(BaseModel):
    metadata: CsvEnvelopeMeta
    csv: list[DrugRow]


class CountriesExportResponse(BaseModel):
    metadata: CsvEnvelopeMeta
    csv: list[CountryRow]


#Routes

@app.get("/health", response_model=HealthResponse, tags=["meta"],
         summary="Liveness check")
def health():
    """Returns API status and whether Neo4j is reachable."""
    neo4j_ok = False
    try:
        with driver.session() as session:
            result = session.run("RETURN 1 AS ok").single()
            neo4j_ok = bool(result and result["ok"] == 1)
    except Exception as exc:
        log.warning("Neo4j health check failed: %s", exc)
    return HealthResponse(status="ok" if neo4j_ok else "degraded",
                          neo4j=neo4j_ok, api_version=app.version)


@app.post("/translate", response_model=TranslateResponse, tags=["translation"],
          summary="Translate a drug name between languages")
def translate_term(body: TranslateRequest):
    """
    Translate a drug name from one language to another.

    - `term`        can be a generic name (Ibuprofen) or a brand name (Advil).
    - `source_lang` ISO 639-1 code of the input language  (e.g. `"en"`).
    - `target_lang` ISO 639-1 code of the desired language (e.g. `"es"`).
    - `country`     ISO 3166-1 alpha-2 to narrow results to one country.

    The response `csv` array contains one row per brand name found in the
    target language, sorted alphabetically by generic_name then brand_name.

    Request:
    ```json
    { "term": "Advil", "source_lang": "en", "target_lang": "es", "country": "MX" }
    ```

    Response:
    ```json
    {
      "metadata": { "generated_at": "...", "row_count": 2, "source": "translate",
                    "sort_order": "generic_name_asc" },
      "term": "Advil",
      "source_lang": "en",
      "target_lang": "es",
      "found": true,
      "csv": [
        { "brand_name": "Advil",   "generic_name": "Ibuprofeno",
          "original_language": "English", "translated_language": "Spanish" },
        { "brand_name": "Anadvil", "generic_name": "Ibuprofeno",
          "original_language": "English", "translated_language": "Spanish" }
      ]
    }
    ```
    """
    log.info("Translate  term=%r  %s → %s  country=%s", body.term, body.source_lang, body.target_lang, body.country)
    try:
        raw = translate(term=body.term,
                        source_lang=body.source_lang,
                        target_lang=body.target_lang,
                        country=body.country)
    except Exception as exc:
        log.exception("translate() raised an unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))

    rows = [TranslateResultRow(**r) for r in raw.get("results", [])]
    meta = CsvEnvelopeMeta(
        generated_at=datetime.now(timezone.utc).isoformat(),
        row_count=len(rows),
        source="translate",
    )
    return TranslateResponse(
        metadata=meta,
        term=raw["term"],
        source_lang=raw["source_lang"],
        target_lang=raw["target_lang"],
        country=raw.get("country"),
        found=raw["found"],
        csv=rows,
    )


@app.get("/audit/{term}", response_model=AuditResponse, tags=["translation"],
         summary="Quality audit for a term")
def audit_term(term: str):
    """
    Returns missing translations, missing brand names, and equivalent brands
    across all known countries for a given term.
    """
    log.info("Audit  term=%r", term)
    try:
        with driver.session() as session:
            canonical   = resolve_to_base_term(session, term) or term
            missing_tx  = find_missing_translations(session, canonical)
            missing_br  = find_missing_brands(session, canonical)
            equivalents = get_equivalent_brands(session, canonical)
    except Exception as exc:
        log.exception("audit raised an unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))

    return AuditResponse(
        term=term,
        canonical=canonical,
        missing_translations=[AuditEntry(**m) for m in missing_tx],
        missing_brands=[AuditEntry(**m) for m in missing_br],
        equivalent_brands=[
            BrandEntry(brand=e["brand"], country=e["country"],
                       country_name=e["country_name"])
            for e in equivalents
        ],
    )


@app.get("/languages", response_model=LanguagesResponse, tags=["meta"],
         summary="List languages loaded in Neo4j")
def list_languages():
    """Returns every language code that has at least one Translation node."""
    try:
        with driver.session() as session:
            records = session.run(
                "MATCH (l:Language) RETURN l.code AS code ORDER BY code"
            )
            codes = [r["code"] for r in records if r["code"]]
        return LanguagesResponse(languages=codes)
    except Exception as exc:
        log.exception("list_languages failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/countries", response_model=CountriesExportResponse, tags=["meta"],
         summary="List supported countries and their languages")
def list_countries():
    """
    Returns every Country node in Neo4j with its associated language(s),
    sorted alphabetically by ISO code.

    Response:
    ```json
    {
      "metadata": { ... },
      "csv": [
        { "iso_code": "MX", "languages": ["Spanish"] },
        { "iso_code": "US", "languages": ["English"] }
      ]
    }
    ```
    """
    try:
        with driver.session() as session:
            rows = get_countries_languages(session)
    except Exception as exc:
        log.exception("list_countries failed")
        raise HTTPException(status_code=500, detail=str(exc))

    country_rows = [CountryRow(**r) for r in rows]
    meta = CsvEnvelopeMeta(
        generated_at=datetime.now(timezone.utc).isoformat(),
        row_count=len(country_rows),
        source="neo4j",
    )
    return CountriesExportResponse(metadata=meta, csv=country_rows)


@app.post("/csv/upload", response_model=CsvUploadResponse,
          status_code=status.HTTP_201_CREATED, tags=["data"],
          summary="Upload a Codex CSV and import drugs into Neo4j")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a Codex-format CSV file and import all drug entries into Neo4j.

    Expected columns:
        DrugBank ID, Generic Name, Brand Name, Country,
        Source Language, Language Code

    One row per (drug, brand, country).  Multiple brands for the same drug
    in the same country = multiple rows with the same Generic Name.

    Response:
    ```json
    {
      "metadata": { "generated_at": "...", "row_count": 10,
                    "source": "drugs_en_US.csv", "sort_order": "generic_name_asc" },
      "message": "Imported 10 drug entries from drugs_en_US.csv"
    }
    ```
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    log.info("CSV upload: %s", file.filename)
    try:
        raw_bytes = await file.read()
        text      = raw_bytes.decode("utf-8-sig")  # handle optional BOM
        reader    = csv.DictReader(io.StringIO(text))
        rows      = list(reader)

        if not rows:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        with driver.session() as session:
            imported = import_csv_drugs(session, rows)

        meta = CsvEnvelopeMeta(
            generated_at=datetime.now(timezone.utc).isoformat(),
            row_count=imported,
            source=file.filename,
        )
        log.info("CSV upload complete: %d rows from %s", imported, file.filename)
        return CsvUploadResponse(
            metadata=meta,
            message=f"Imported {imported} drug entries from {file.filename}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("csv_upload failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/csv", response_model=CsvExportResponse, tags=["data"],
         summary="Export full drug catalogue sorted alphabetically")
def export_csv():
    """
    Returns all drug–brand pairs stored in Neo4j as a JSON envelope, sorted
    alphabetically by generic_name ascending.

    Each row contains:
    - `generic_name`        — drug name in its source language
    - `brand_name`          — commercial brand name (returns null if none)
    - `country`             — ISO country code
    - `original_language`   — source language for this entry
    - `translated_language` — language of the translation node (same as source
                              for entry checking, will only see on csv list)

    Response:
    ```json
    {
      "metadata": { "generated_at": "...", "row_count": 10,
                    "source": "neo4j", "sort_order": "generic_name_asc" },
      "csv": [
        { "generic_name": "Ibuprofen", "brand_name": "Advil",
          "country": "US", "original_language": "English",
          "translated_language": "English" },
        ...
      ]
    }
    ```
    """
    try:
        with driver.session() as session:
            rows = get_drugs_table(session)
    except Exception as exc:
        log.exception("export_csv failed")
        raise HTTPException(status_code=500, detail=str(exc))

    drug_rows = [DrugRow(**r) for r in rows]
    meta = CsvEnvelopeMeta(
        generated_at=datetime.now(timezone.utc).isoformat(),
        row_count=len(drug_rows),
        source="neo4j",
    )
    return CsvExportResponse(metadata=meta, csv=drug_rows)


#Entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    log.info("Starting Codex API on port %d", port)
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
