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
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
from pathlib import Path
import ast
from pydantic import BaseModel, field_serializer
from dotenv import load_dotenv

import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from neo4j_sources.source_data import source_data
from ocr.ocrmatching import router as ocr_router


# ── Load .env before importing codex (which reads env vars at module level) ──
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── JSON Web Token (JWT) setup and functions ─────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-fallback-key-32bytespls")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24   # access lasts for 24 hours

security = HTTPBearer(auto_error=False)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Decodes JWT and returns the current database-backed user identity and role."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = str(payload.get("sub", "")).lower().strip()

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with driver.session() as session:
        user = get_user_by_email(session, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload["sub"] = user["email"]
    payload["role"] = user["role"]
    return payload

def require_roles(allowed_roles: List[str]):
    """Enforces that the current authenticated user belongs to one of the allowed roles."""
    def role_checker(current_user: Optional[dict] = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_role = current_user.get("role", "").lower()
        allowed_lower = [r.lower() for r in allowed_roles]
        if user_role not in allowed_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation"
            )
        return current_user
    return role_checker

# ── Import backend package ───────────────────────────────────────────────────
try:
    from codex.services.translation_service import (
        translate,
        load_language_pack,
    )
    from codex.neo4j_driver import (
        driver,
        language_exists,
        find_missing_translations,
        find_missing_brands,
        get_equivalent_brands,
        search_database,
        resolve_to_base_term,
        get_translation_data,
        get_countries_for_term,
        get_languages_for_term,
        get_countries_for_brand,
        get_languages_for_brand,
        create_user,
        get_user_by_email,
        get_all_users,
        update_user,
        delete_user,
        get_user_role,
        count_administrators,
        get_users_by_role,
        update_user_role,
        authenticate_user,
        init_default_admin
    )
except Exception as exc:
    logging.critical("Failed to import codex backend: %s", exc)
    raise exc

# ── App setup ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("codex.api")

BASE_DIR = Path(__file__).resolve().parent
TARGET_FOLDER_PATH = BASE_DIR / "codex" / "language_packs"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # seed default admin user
    init_default_admin()
    
    # scan for and load language packs
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
    allow_origins=[
        "http://localhost:9000",
        "http://localhost:9001",
        "http://localhost:9002",
        "http://localhost:9003",
        "http://localhost:9004",
        "http://localhost:9005",
        "http://localhost:9006",
        "http://localhost:9007",
        "http://localhost:9008",
        "http://localhost:9009",
        "http://localhost:9010",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr_router)

class SourceSelection(BaseModel):
    selectedSources: List[str]
    DBAPIKey: str
    ICDID: str
    ICDSecret: str

@app.post(
    "/api/populate-sources",
    tags=["data"],
    dependencies=[Depends(require_roles(["medical professional", "administrator"]))],
)
async def handle_populate(data: SourceSelection):
    sources = data.selectedSources
    drugbankAPIKey = data.DBAPIKey
    icdID = data.ICDID
    icdSecret= data.ICDSecret
    return StreamingResponse(
        source_data(sources, drugbankAPIKey, icdID, icdSecret),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no", 
            "Connection": "keep-alive",
        }
    )

# ── Request / response models ────────────────────────────────────────────────

class SearchResponse(BaseModel):
    source_id: str
    source_name: str
    name: str
    brand: Optional[str]
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

class UserCreateRequest(BaseModel):
    real_name: str
    password: str
    role: str
    affiliation: str
    email: str

    model_config = {"json_schema_extra": {"example": {
        "real_name": "Jane Doe",
        "password": "SecurePassword123!",
        "role": "Admin",
        "affiliation": "Global Health Org",
        "email": "jane.doe@example.com"
    }}}

class UserUpdateRequest(BaseModel):
    real_name: Optional[str] = None
    role: Optional[str] = None
    affiliation: Optional[str] = None
    password: Optional[str] = None

class UserRoleUpdateRequest(BaseModel):
    role: str

class UserResponse(BaseModel):
    email: str
    real_name: str
    role: str
    affiliation: str
    created_at: Optional[Any] = None

    @field_serializer("created_at")
    def serialize_created_at(self, created_at: Any, _info):
        if created_at is not None:
            return str(created_at)
        return None

class UserRoleResponse(BaseModel):
    email: str
    role: str

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


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
    response_model=List[SearchResponse],
    tags=["translation"],
)
def search(term: str):
    search_results = []
    try:
        with driver.session() as session:
            results = search_database(session, term)
            if not results:
                return []
            for result in results:
                canonical = result[0]
                brand = result[1]
                if not brand:
                    countries = get_countries_for_term(session, canonical)
                    languages = get_languages_for_term(session, canonical)
                    search_results.append(SearchResponse(
                        source_id="0",
                        source_name="",
                        name=canonical,
                        # Include brand name even if generic drug is searched
                        brand=brand,
                        type="drug",
                        country=countries,
                        language=languages,
                        uploaded_at=""
                    ))
                else:
                    countries = get_countries_for_brand(session, brand)
                    languages = get_languages_for_brand(session, brand)
                    search_results.append(SearchResponse(
                        source_id="0",
                        source_name="",
                        name=canonical,
                        brand=brand,
                        type="brand name drug",
                        country=countries,
                        language=languages,
                        uploaded_at=""
                    ))
    except Exception as exc:
        log.exception("search raised an unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))
    
    return search_results

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
    # Build dynamic language map
    LANGUAGE_MAP = {
        "fr": "french",
        "es": "spanish",
        "en": "english",
        "ru": "russian",
        "uk": "ukrainian",
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

    resolved_canonical = raw.get("canonical") if isinstance(raw, dict) and raw.get("canonical") else body.term

    return TranslateResponse(
        canonical=resolved_canonical,
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
    "/packs/load",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and load a language pack",
    tags=["data"],
    dependencies=[Depends(require_roles(["medical professional", "administrator"]))],
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
    
@app.post(
    "/api/login",
    response_model=TokenResponse,
    summary="Authenticate user",
    tags=["auth"],
)
def login(body: LoginRequest):
    """Authenticate a user and return a JWT access token with the current role."""
    with driver.session() as session:
        user = authenticate_user(session, body.email, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        {
            "sub": user["email"],
            "role": user["role"],
        }
    )

    return TokenResponse(
        access_token=access_token,
        role=user["role"],
    )


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    tags=["users"],
    dependencies=[Depends(require_roles(["administrator"]))],
)
def api_create_user(body: UserCreateRequest):
    """Create a new user in Neo4j. Returns 409 if the email already exists."""
    try:
        with driver.session() as session:
            # Check if user already exists
            existing = get_user_by_email(session, body.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User with email '{body.email}' already exists."
                )
            
            user = create_user(
                session,
                real_name=body.real_name,
                password=body.password,
                role=body.role,
                affiliation=body.affiliation,
                email=body.email
            )
            if not user:
                raise HTTPException(status_code=500, detail="Failed to create user node.")
            return user
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("api_create_user failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users or filter by role",
    tags=["users"],
    dependencies=[Depends(require_roles(["administrator"]))],
)
def api_get_users(
    role: Optional[str] = Query(None, description="Optional role filter"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Return users from Neo4j, optionally filtered by role and limited by count."""
    try:
        with driver.session() as session:
            if role:
                return get_users_by_role(session, role)
            return get_all_users(session, limit=limit)
    except Exception as exc:
        log.exception("api_get_users failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/users/{email}",
    response_model=UserResponse,
    summary="Get user by email",
    tags=["users"],
    dependencies=[Depends(require_roles(["administrator"]))],
)
def api_get_user(email: str):
    """Return a single user by email. Returns 404 when the user does not exist."""
    try:
        with driver.session() as session:
            user = get_user_by_email(session, email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{email}' not found."
                )
            return user
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("api_get_user failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch(
    "/users/{email}",
    response_model=UserResponse,
    summary="Update user details",
    tags=["users"],
    dependencies=[Depends(require_roles(["administrator"]))],
)
def api_update_user(email: str, body: UserUpdateRequest):
    """Update user profile fields and prevent demotion of the last administrator."""
    try:
        with driver.session() as session:
            if body.role is not None:
                current_role = get_user_role(session, email)

                if (
                    current_role is not None
                    and current_role.strip().lower() == "administrator"
                    and body.role.strip().lower() != "administrator"
                    and count_administrators(session) <= 1
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot demote the last administrator."
                    )

            updated = update_user(
                session,
                email=email,
                real_name=body.real_name,
                role=body.role,
                affiliation=body.affiliation,
                password=body.password
            )
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{email}' not found or no changes were made."
                )
            return updated
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("api_update_user failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete(
    "/users/{email}",
    response_model=MessageResponse,
    summary="Delete a user",
    tags=["users"],
    dependencies=[Depends(require_roles(["administrator"]))],
)
def api_delete_user(
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a user while preventing administrator self-deletion and removal of the last administrator."""
    try:
        with driver.session() as session:
            role = get_user_role(session, email)

            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{email}' not found."
                )

            current_email = str(current_user.get("sub", "")).lower().strip()

            if email.lower().strip() == current_email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Administrators cannot delete their own account."
                )

            if (
                role.strip().lower() == "administrator"
                and count_administrators(session) <= 1
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete the last administrator."
                )

            deleted = delete_user(session, email)

            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{email}' not found."
                )
            return MessageResponse(message=f"User '{email}' deleted successfully.")
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("api_delete_user failed")
        raise HTTPException(status_code=500, detail=str(exc))

@app.get(
    "/users/{email}/role",
    response_model=UserRoleResponse,
    summary="Get a user's role",
    tags=["users"],
    dependencies=[Depends(require_roles(["administrator"]))],
)
def api_get_user_role(email: str):
    """Return the role assigned to a user. Returns 404 when the user does not exist."""
    try:
        with driver.session() as session:
            role = get_user_role(session, email)
            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{email}' not found."
                )
            return UserRoleResponse(email=email, role=role)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("api_get_user_role failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.put(
    "/users/{email}/role",
    response_model=UserResponse,
    summary="Update a user's role",
    tags=["users"],
    dependencies=[Depends(require_roles(["administrator"]))],
)
def api_update_user_role(email: str, body: UserRoleUpdateRequest):
    """Update a user role while preventing demotion of the last administrator."""
    try:
        with driver.session() as session:
            current_role = get_user_role(session, email)

            if current_role is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{email}' not found."
                )

            if (
                current_role.strip().lower() == "administrator"
                and body.role.strip().lower() != "administrator"
                and count_administrators(session) <= 1
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot demote the last administrator."
                )

            updated = update_user_role(session, email=email, new_role=body.role)
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{email}' not found."
                )
            return updated
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("api_update_user_role failed")
        raise HTTPException(status_code=500, detail=str(exc))

# ── Entry point (for running directly) ──────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    log.info("Starting Codex API on port %d", port)
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
