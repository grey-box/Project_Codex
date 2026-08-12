"""
Codex Translation API
=====================
FastAPI service that sits between the CLI (or any HTTP client) and the
Neo4j-backed translation engine.

All business logic lives in codex/.  This file only:
  - Defines request / response shapes (Pydantic models)
  - Routes HTTP calls to the right backend function
  - Formats errors consistently

Endpoints
---------
  GET  /health              Liveness check — API + Neo4j
  POST /translate           Translate a drug term
  GET  /audit/{term}        Quality audit (missing translations / brands)
  POST /demo/load           Load built-in sample data
  POST /packs/load          Upload and load a language pack JSON
  GET  /languages           List language codes that have data in Neo4j
"""

from __future__ import annotations

import os
import sys
import tempfile
import logging
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
import ast
from pydantic import BaseModel
from dotenv import load_dotenv

from neo4j_sources.source_data import source_data

# ── Load .env before importing codex (which reads env vars at module level) ──
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Import backend package ───────────────────────────────────────────────────
try:
    from codex.services.translation_service import (
        translate,
        load_language_pack,
        load_demo_data,
    )
    from codex.neo4j_driver import (
        driver,
        language_exists,
        find_missing_translations,
        find_missing_brands,
        get_equivalent_brands,
        resolve_to_base_term,
        get_translation_data
    )
except Exception as exc:
    logging.critical("Failed to import codex backend: %s", exc)
    sys.exit(1)

# ── App setup ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("codex.api")

TARGET_FOLDER_PATH = Path("./codex/language_packs")
@asynccontextmanager
async def lifespan(app: FastAPI):
    demo_load()
    print(f"Scanning directory: {TARGET_FOLDER_PATH.resolve()}")
    
    if TARGET_FOLDER_PATH.exists() and TARGET_FOLDER_PATH.is_dir():
        # Iterate over every file in the target folder
        for file_path in TARGET_FOLDER_PATH.iterdir():
            if file_path.is_file():
                print(f"Found file: {file_path.name}")
                
                # Open the local file from disk
                with open(file_path, "rb") as f:
                    # Construct a FastAPI UploadFile object dynamically
                    upload_file = UploadFile(
                        filename=file_path.name,
                        file=f
                    )
                    
                    # Call your load_pack function for each file
                    await load_pack(upload_file)
    else:
        print(f"Warning: Directory '{TARGET_FOLDER_PATH}' does not exist.")

    yield 

app = FastAPI(
    title="Codex Medical Translation API",
    description="Translate drug names across languages and countries using Neo4j.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SourceSelection(BaseModel):
    selectedSources: List[str]

@app.post("/api/populate-sources")
async def handle_populate(data: SourceSelection):
    sources = data.selectedSources
    
    source_data(sources)
    
    return {"status": "success", "message": "Successfully populated Neo4j!"}


# ── Request / response models ────────────────────────────────────────────────

class SearchResponse(BaseModel):
    source_id: str
    source_name: str
    name: str
    type: str
    country: str
    language: str
    uploaded_at: str

class TranslateRequest(BaseModel):
    term: str
    lang: str
    country: str

    model_config = {"json_schema_extra": {"example": {
        "term": "ibuprofen",
        "lang": "es",
        "country": "MX",
    }}}

class TranslationResult(BaseModel):
    translation: str
    language: str
    brand: Optional[str]
    country: Optional[str]


class TranslateResponse(BaseModel):
    canonical: str
    results: list[TranslationResult]


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


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    neo4j: bool
    api_version: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    tags=["meta"],
)
def health():
    """Returns API status and whether Neo4j is reachable."""
    neo4j_ok = False
    try:
        with driver.session() as session:
            result = session.run("RETURN 1 AS ok").single()
            neo4j_ok = result and result["ok"] == 1
    except Exception as exc:
        log.warning("Neo4j health check failed: %s", exc)

    return HealthResponse(
        status="ok" if neo4j_ok else "degraded",
        neo4j=neo4j_ok,
        api_version=app.version,
    )

@app.post(
    "/search",
    response_model=SearchResponse | None,
    tags=["search"],
)
def search(term: str):
    try:
        with driver.session() as session:
            canonical = resolve_to_base_term(session, term)
            if not canonical:
                return None
    except Exception as exc:
        log.exception("search raised an unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))

    return SearchResponse(
        source_id="0",
        source_name="",
        name=canonical,
        type="drug",
        country="US",
        language="en",
        uploaded_at=""
    )

@app.post(
    "/translate",
    response_model=TranslateResponse,
    summary="Translate a drug term",
    tags=["translation"],
)
def translate_term(body: TranslateRequest):
    """
    Translate a medical term into the requested language.

    - Resolves brand names and fuzzy input to a canonical term first.
    - Falls back through configured language chains if no direct match.

    JSON SETUP
      incoming
      { "term": "ibuprofen", "source_lang": "en", "target_lang": "es", "country": "MX" }
      
      outgoing
      {
      "canonical": "ibuprofen",
      "results": [
        { "translation": "ibuprofeno", "language": "Spanish", "brand": "Advil", "country": "MX" }
      ]
      }
    """
    log.info("Translate  term=%r  lang=%s  country=%s", body.term, body.lang, body.country)

    try:
        raw_data = translate(term=body.term, lang=body.lang, country=body.country)
        if isinstance(raw_data, str):
            raw = ast.literal_eval(raw_data)
        else:
            raw = raw_data
    except Exception as exc:
        log.exception("translate() raised an unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))

    raw_results = raw.get("results", []) if isinstance(raw, dict) else []
    target_lang_str = (body.lang or "").strip().lower()
    LANGUAGE_MAP = {
        "fr": "french",
        "es": "spanish",
        "en": "english",
        "ru": "russian",
        "ua": "ukrainian",
    }
    mapped_lang_name = LANGUAGE_MAP.get(target_lang_str, target_lang_str)

    results = [
        TranslationResult(
            translation=r.get("translation", ""),
            language=r.get("language", ""),
            brand=r.get("brand"),
            country=r.get("country"),
        )
        for r in raw_results
        if (
            not body.lang 
            or str(r.get("language", "")).lower() == target_lang_str
            or str(r.get("lang_code", "")).lower() == target_lang_str
            or str(r.get("language_code", "")).lower() == target_lang_str
            or str(r.get("language", "")).lower() == mapped_lang_name
        )
        and (
            not body.country 
            or str(r.get("country", "")).lower() == body.country.lower()
        )
    ]

    return TranslateResponse(
        canonical=body.term,
        results=results,
    )


@app.get(
    "/audit/{term}",
    response_model=AuditResponse,
    summary="Quality audit for a term",
    tags=["translation"],
)
def audit_term(term: str):
    """
    Returns:
    - Countries where this term has no translation
    - Countries where this term has no brand name
    - All equivalent brand names across countries
    """
    log.info("Audit  term=%r", term)

    try:
        with driver.session() as session:
            canonical = resolve_to_base_term(session, term) or term
            missing_tx   = find_missing_translations(session, canonical)
            missing_br   = find_missing_brands(session, canonical)
            equivalents  = get_equivalent_brands(session, canonical)
    except Exception as exc:
        log.exception("audit raised an unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))

    return AuditResponse(
        term=term,
        canonical=canonical,
        missing_translations=[AuditEntry(**m) for m in missing_tx],
        missing_brands=[AuditEntry(**m) for m in missing_br],
        equivalent_brands=[
            BrandEntry(brand=e["brand"], country=e["country"], country_name=e["country_name"])
            for e in equivalents
        ],
    )


@app.post(
    "/demo/load",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Load built-in sample data",
    tags=["data"],
)
def demo_load():
    """
    Loads Ibuprofen, Paracetamol, and Amoxicillin with translations across
    US, GB, FR, ES, MX, NG, IN into Neo4j.

    Safe to call multiple times (uses MERGE — no duplicates).
    """
    log.info("Loading demo data")
    try:
        result = load_demo_data()
        return MessageResponse(message=result.get("status", "Demo data loaded"))
    except Exception as exc:
        log.exception("demo_load failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/packs/load",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and load a language pack",
    tags=["data"],
)
async def load_pack(file: UploadFile = File(...)):
    """
    Upload a language pack JSON file and load it into Neo4j.

    The file must follow the standard pack format:
    ```json
    {
      "language": {"code": "pt", "name": "Portuguese"},
      "terms": [
        {
          "canonical": "Ibuprofen",
          "entries": [
            {"translation": "ibuprofeno", "country": "BR", "brand": "Advil"}
          ]
        }
      ]
    }
    ```
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json language pack")

    log.info("Loading language pack: %s", file.filename)

    # Write to a temp file so load_language_pack() (which expects a path) works
    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        message = load_language_pack(tmp_path)
        return MessageResponse(message=message)
    except Exception as exc:
        log.exception("load_pack failed")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get(
    "/languages",
    response_model=LanguagesResponse,
    summary="List languages with data in Neo4j",
    tags=["meta"],
)
def list_languages():
    """Returns every language code that has at least one translation node in Neo4j."""
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


# ── Entry point (for running directly) ──────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    log.info("Starting Codex API on port %d", port)
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
