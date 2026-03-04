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
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

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
    )
except Exception as exc:
    logging.critical("Failed to import codex backend: %s", exc)
    sys.exit(1)

# ── App setup ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("codex.api")

app = FastAPI(
    title="Codex Medical Translation API",
    description="Translate drug names across languages and countries using Neo4j.",
    version="1.0.0",
)


# ── Request / response models ────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    term: str
    lang: Optional[str] = None
    country: Optional[str] = None

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
    requested_language: Optional[str]
    used_language: Optional[str]
    fallback_used: bool
    fallback_type: Optional[str] = None
    fallback_chain: Optional[list[str]] = None
    missing_language_pack: Optional[bool] = None
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
    - Falls back to English as the last resort.
    - Returns `missing_language_pack: true` if the language has no data loaded.
    """
    log.info("Translate  term=%r  lang=%s  country=%s", body.term, body.lang, body.country)

    try:
        raw = translate(term=body.term, lang=body.lang, country=body.country)
    except Exception as exc:
        log.exception("translate() raised an unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))

    results = [
        TranslationResult(
            translation=r["translation"],
            language=r["language"],
            brand=r.get("brand"),
            country=r.get("country"),
        )
        for r in raw.get("results", [])
    ]

    return TranslateResponse(
        canonical=raw.get("canonical", body.term),
        requested_language=raw.get("requested_language"),
        used_language=raw.get("used_language"),
        fallback_used=raw.get("fallback_used", False),
        fallback_type=raw.get("fallback_type"),
        fallback_chain=raw.get("fallback_chain"),
        missing_language_pack=raw.get("missing_language_pack"),
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
