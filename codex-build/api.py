"""
Codex Translation API v3.0
FastAPI service — all business logic lives in codex/

Endpoints
---------
  GET  /health                 Liveness check
  POST /translate              Translate a drug name between languages
  GET  /csv                    All terms in the database
  GET  /csv/concept/{id}       All terms for a Concept ID
  GET  /csv/country/{country}  All terms for a country
  GET  /csv/language/{lang}    All terms for a language
  GET  /sources                List all sources
  GET  /sources/{name}         All terms from a specific source
  GET  /countries              All countries and their languages
  GET  /languages              All languages in the database
  POST /csv/upload             Upload a Codex CSV
  POST /reset                  Wipe all data
  POST /shutdown               Graceful shutdown
"""

from __future__ import annotations

import csv
import io
import os
import sys
import time
import signal
import logging
import threading
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
        import_csv_drugs,
        translate_term,
        get_all_terms,
        get_terms_by_concept,
        get_terms_by_country,
        get_terms_by_language,
        get_sources,
        get_terms_by_source,
        get_countries,
        get_languages,
        reset_database,
    )
except Exception as exc:
    logging.critical("Failed to import codex backend: %s", exc)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("codex.api")

app = FastAPI(
    title="Codex Medical Translation API",
    description="Translate drug and medical terms across languages.",
    version="3.0.0",
)


# Pydantic models

class TermRow(BaseModel):
    source_id:   Optional[str] = None
    source_name: Optional[str] = None
    name:        str
    type:        str
    country:     Optional[str] = None
    language:    Optional[str] = None
    uploaded_at: Optional[str] = None


class TranslateRequest(BaseModel):
    term:           str
    source_lang:    str
    target_lang:    str
    target_country: Optional[str] = None
    source_name:    Optional[str] = None

    model_config = {"json_schema_extra": {"example": {
        "term": "Ibuprofen", "source_lang": "en", "target_lang": "es",
        "target_country": "MX", "source_name": None,
    }}}


class TranslateResponse(BaseModel):
    term:           str
    source_lang:    str
    target_lang:    str
    target_country: Optional[str]
    source_name:    Optional[str]
    found:          bool
    results:        list[TermRow]


class TermsResponse(BaseModel):
    generated_at: str
    row_count:    int
    rows:         list[TermRow]


class SourceRow(BaseModel):
    source_name:    str
    term_count:     int
    last_uploaded:  Optional[str] = None


class SourcesResponse(BaseModel):
    sources: list[SourceRow]


class CountryRow(BaseModel):
    country:   str
    languages: list[str]


class CountriesResponse(BaseModel):
    countries: list[CountryRow]


class LanguagesResponse(BaseModel):
    languages: list[str]


class HealthResponse(BaseModel):
    status:      str
    neo4j:       bool
    api_version: str


class UploadResponse(BaseModel):
    generated_at: str
    row_count:    int
    filename:     str
    message:      str


class ResetResponse(BaseModel):
    status:  str
    message: str


class ShutdownResponse(BaseModel):
    status: str


def _terms_response(rows: list) -> TermsResponse:
    return TermsResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        row_count=len(rows),
        rows=[TermRow(**r) for r in rows],
    )


# Routes

@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health():
    neo4j_ok = False
    try:
        with driver.session() as session:
            result = session.run("RETURN 1 AS ok").single()
            neo4j_ok = bool(result and result["ok"] == 1)
    except Exception as exc:
        log.warning("Neo4j health check failed: %s", exc)
    return HealthResponse(
        status="ok" if neo4j_ok else "degraded",
        neo4j=neo4j_ok,
        api_version=app.version,
    )


@app.post("/translate", response_model=TranslateResponse, tags=["translation"])
def translate_drug(body: TranslateRequest):
    """
    Translate a drug name from one language to another via shared Concept ID.

    Optionally filter results by target_country and/or source_name.
    """
    log.info("Translate %r  %s → %s  country=%s  source=%s",
             body.term, body.source_lang, body.target_lang,
             body.target_country, body.source_name)
    try:
        raw = translate(
            term=body.term,
            source_lang=body.source_lang,
            target_lang=body.target_lang,
            target_country=body.target_country,
            source_name=body.source_name,
        )
    except Exception as exc:
        log.exception("translate() error")
        raise HTTPException(status_code=500, detail=str(exc))

    return TranslateResponse(
        term=raw["term"],
        source_lang=raw["source_lang"],
        target_lang=raw["target_lang"],
        target_country=raw.get("target_country"),
        source_name=raw.get("source_name"),
        found=raw["found"],
        results=[TermRow(**r) for r in raw["results"]],
    )


@app.get("/csv", response_model=TermsResponse, tags=["data"])
def list_all_terms():
    """Return every term in the database sorted alphabetically."""
    try:
        with driver.session() as session:
            rows = get_all_terms(session)
    except Exception as exc:
        log.exception("list_all_terms failed")
        raise HTTPException(status_code=500, detail=str(exc))
    return _terms_response(rows)


@app.get("/csv/concept/{concept_id}", response_model=TermsResponse, tags=["data"])
def list_terms_by_concept(concept_id: str):
    """Return all terms linked to a given Concept ID."""
    try:
        with driver.session() as session:
            rows = get_terms_by_concept(session, concept_id)
    except Exception as exc:
        log.exception("list_terms_by_concept failed")
        raise HTTPException(status_code=500, detail=str(exc))
    if not rows:
        raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found")
    return _terms_response(rows)


@app.get("/csv/country/{country}", response_model=TermsResponse, tags=["data"])
def list_terms_by_country(country: str):
    """Return all terms for a given country ISO code."""
    try:
        with driver.session() as session:
            rows = get_terms_by_country(session, country)
    except Exception as exc:
        log.exception("list_terms_by_country failed")
        raise HTTPException(status_code=500, detail=str(exc))
    if not rows:
        raise HTTPException(status_code=404, detail=f"No terms found for country '{country}'")
    return _terms_response(rows)


@app.get("/csv/language/{language}", response_model=TermsResponse, tags=["data"])
def list_terms_by_language(language: str):
    """Return all terms for a given language (ISO code or full name)."""
    try:
        with driver.session() as session:
            rows = get_terms_by_language(session, language)
    except Exception as exc:
        log.exception("list_terms_by_language failed")
        raise HTTPException(status_code=500, detail=str(exc))
    if not rows:
        raise HTTPException(status_code=404, detail=f"No terms found for language '{language}'")
    return _terms_response(rows)


@app.get("/sources", response_model=SourcesResponse, tags=["data"])
def list_sources():
    """Return all sources with term counts and latest upload timestamp."""
    try:
        with driver.session() as session:
            rows = get_sources(session)
    except Exception as exc:
        log.exception("list_sources failed")
        raise HTTPException(status_code=500, detail=str(exc))
    return SourcesResponse(sources=[SourceRow(**r) for r in rows])


@app.get("/sources/{source_name}", response_model=TermsResponse, tags=["data"])
def list_terms_by_source(source_name: str):
    """Return all terms from a specific source."""
    try:
        with driver.session() as session:
            rows = get_terms_by_source(session, source_name)
    except Exception as exc:
        log.exception("list_terms_by_source failed")
        raise HTTPException(status_code=500, detail=str(exc))
    if not rows:
        raise HTTPException(status_code=404, detail=f"Source '{source_name}' not found")
    return _terms_response(rows)


@app.get("/countries", response_model=CountriesResponse, tags=["meta"])
def list_countries():
    """Return all countries present in the database with their languages."""
    try:
        with driver.session() as session:
            rows = get_countries(session)
    except Exception as exc:
        log.exception("list_countries failed")
        raise HTTPException(status_code=500, detail=str(exc))
    return CountriesResponse(countries=[CountryRow(**r) for r in rows])


@app.get("/languages", response_model=LanguagesResponse, tags=["meta"])
def list_languages():
    """Return all distinct languages present in the database."""
    try:
        with driver.session() as session:
            langs = get_languages(session)
    except Exception as exc:
        log.exception("list_languages failed")
        raise HTTPException(status_code=500, detail=str(exc))
    return LanguagesResponse(languages=langs)


@app.post("/csv/upload", response_model=UploadResponse,
          status_code=status.HTTP_201_CREATED, tags=["data"])
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a Codex CSV and import all entries into Neo4j.

    Expected columns:
        Concept ID, Source ID, Source Name, Name, Type, Country, Language

    Concept ID is optional — a UUID is generated automatically for blank values.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    log.info("CSV upload: %s", file.filename)
    try:
        raw_bytes = await file.read()
        text      = raw_bytes.decode("utf-8-sig")
        rows      = list(csv.DictReader(io.StringIO(text)))

        if not rows:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        ts = datetime.now(timezone.utc).isoformat()
        with driver.session() as session:
            imported = import_csv_drugs(session, rows, uploaded_at=ts)

        log.info("Imported %d rows from %s", imported, file.filename)
        return UploadResponse(
            generated_at=ts,
            row_count=imported,
            filename=file.filename,
            message=f"Imported {imported} entries from {file.filename}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("csv_upload failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/reset", response_model=ResetResponse, tags=["meta"])
def reset_db():
    """Delete every node and relationship from Neo4j. Irreversible."""
    try:
        with driver.session() as session:
            reset_database(session)
        log.warning("Database reset — all data wiped")
        return ResetResponse(status="ok", message="Database wiped successfully")
    except Exception as exc:
        log.exception("reset failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/shutdown", response_model=ShutdownResponse, tags=["meta"])
def shutdown_app():
    """Signal the application to shut down cleanly."""
    def _deferred_exit():
        time.sleep(0.3)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=_deferred_exit, daemon=True).start()
    return ShutdownResponse(status="shutting_down")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    log.info("Starting Codex API on port %d", port)
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
