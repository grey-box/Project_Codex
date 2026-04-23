# Codex — Developer Setup Guide (Docker)

This guide is for **development and feature testing only**.  
For the final application setup, see `README.md`.

Docker gives you a disposable Neo4j instance that starts and stops
instantly — ideal for testing new features, experimenting with data,
or running the API in isolation without touching your local environment.

---

## Prerequisites

| Tool                  | Version      | Purpose              |
|-----------------------|--------------|----------------------|
| Python                | 3.10+        | API and CLI          |
| Docker + Docker Compose | any recent | Neo4j database       |
| pip                   | any          | Python dependencies  |

---

## Quick start

```
1. docker-compose up -d          # start Neo4j in the background
2. cp .env.example .env          # configure credentials (first time only)
3. pip install -r requirements.txt
4. python api.py                 # start the API
5. python cli.py                 # open the CLI
```

> **macOS / Linux:** use `python3` in place of `python` above.

---

## Step 1 — Start Neo4j

```bash
docker-compose up -d
```

This starts Neo4j 5.18 with the APOC plugin and exposes two ports:

| Port | Use                                                  |
|------|------------------------------------------------------|
| 7474 | Neo4j Browser — http://localhost:7474 (neo4j/changeme) |
| 7687 | Bolt — used by the API                               |

Wait ~30 seconds for Neo4j to finish initialising before starting the API.
Watch progress with:

```bash
docker-compose logs -f neo4j
```

---

## Step 2 — Configure credentials

```bash
cp .env.example .env
```

The defaults match `docker-compose.yml` exactly.  Edit `.env` only if
you have changed the Neo4j credentials.

---

## Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Start the API

```bash
python api.py
```

Or with auto-reload during development:

```bash
uvicorn api:app --reload
```

Swagger UI is available at **http://localhost:8000/docs**

---

## Step 5 — Verify

```
python cli.py
codex> health
```

Expected output:
```
  API   : ✓ running  (v2.0.0)
  Neo4j : ✓ connected
```

---

## Step 6 — Load drug data

```
codex> csv upload sample_data/drugs_en_US.csv
codex> csv upload sample_data/drugs_es_MX.csv
```

Verify what was loaded:

```
codex> languages          # shows: en, es
codex> countries          # shows: MX (Spanish), US (English)
codex> csv list           # full catalogue sorted alphabetically
```

---

## Step 7 — Translate a drug

```
codex> translate
  Drug name (generic or brand): Advil
  Source language code (e.g. en, es, fr): en
  Target language code (e.g. es, uk, fr): es
  Country code (e.g. US, MX) or Enter to search all: MX
```

---

## Managing Neo4j data

Docker persists Neo4j data in a named volume between `docker-compose up`
and `docker-compose down` cycles.  Use the commands below intentionally:

```bash
docker-compose down          # stop Neo4j — data is preserved
docker-compose down -v       # stop Neo4j and WIPE all data (clean slate)
docker-compose restart       # restart without touching data
```

> **Tip:** `docker-compose down -v` is useful when you want to reset the
> database to a blank state for a clean test run.

---

## Dev workflow tips

**Auto-reload the API on code changes:**
```bash
uvicorn api:app --reload
```

**Inspect the database directly:**  
Open http://localhost:7474 in your browser, log in with `neo4j / changeme`,
and run Cypher queries directly against the live data.

**Reset and re-seed quickly:**
```bash
docker-compose down -v       # wipe data
docker-compose up -d         # fresh Neo4j
# wait ~30s then:
python cli.py
codex> csv upload sample_data/drugs_en_US.csv
codex> csv upload sample_data/drugs_es_MX.csv
```

---

## Stopping Neo4j

```bash
docker-compose down          # stop, keep data
docker-compose down -v       # stop, wipe data
```

---

## Differences from the production setup

| | Docker (dev) | Launcher (production) |
|---|---|---|
| Neo4j start | `docker-compose up -d` | automatic via `launcher.py` |
| API start | `python api.py` (separate) | automatic via `launcher.py` |
| Data location | Docker named volume | OS app-support directory |
| Data reset | `docker-compose down -v` | delete data directory manually |
| First boot time | ~30s | ~30s (first launch only) |
| Requires Docker | yes | no |

---

## API reference

| Method | Path            | Description                                   |
|--------|-----------------|-----------------------------------------------|
| GET    | `/health`       | Liveness check — API + Neo4j                  |
| POST   | `/translate`    | Translate a drug name between languages       |
| GET    | `/audit/{term}` | Quality audit (missing translations / brands) |
| GET    | `/languages`    | List language codes loaded in Neo4j           |
| GET    | `/countries`    | List supported countries and their languages  |
| POST   | `/csv/upload`   | Upload a Codex CSV → Neo4j                    |
| GET    | `/csv`          | Export full drug catalogue (sorted)           |
| POST   | `/shutdown`     | Gracefully shut down the application          |

### POST /translate — request body

```json
{
  "term":        "Advil",
  "source_lang": "en",
  "target_lang": "es",
  "country":     "MX"
}
```

`term` accepts both generic names (`Ibuprofen`) and brand names (`Advil`).  
`country` is optional — omit it to return results across all countries.
