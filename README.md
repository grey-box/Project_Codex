Codex — Setup Guide

Prerequisites


| Tool                    | Version    | Purpose                           |
| ----------------------- | ---------- | --------------------------------- |
| Python                  | 3.10+      | API and CLI                       |
| Docker + Docker Compose | any recent | Full stack (Neo4j, API, Frontend) |
| pip                     | any        | Python dependencies               |


---

## Quick start (Docker)

```bash
docker compose up --build
```

Wait ~30 seconds for Neo4j, API, and Frontend to be ready.

- **Frontend UI:** [http://localhost:9000](http://localhost:9000) (or ports 9000-9010)
- **API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Neo4j Browser:** [http://localhost:7474](http://localhost:7474) (login: `neo4j` / `changeme`)

---

## Manual Setup (Step by Step)

### Step 1 — Start Neo4j

```bash
docker compose up -d neo4j
```

This starts Neo4j 5.18 with the APOC plugin (required for fuzzy matching) and exposes two ports:


| Port | Use                                                                                          |
| ---- | -------------------------------------------------------------------------------------------- |
| 7474 | Neo4j Browser — [http://localhost:7474](http://localhost:7474) (login: `neo4j` / `changeme`) |
| 7687 | Bolt — used by the API                                                                       |


Wait ~30 seconds for Neo4j to finish initialising before starting the API. Watch progress with:

```bash
docker compose logs -f neo4j
```

---

### Step 2 — Configure credentials

```bash
cp .env.example .env
```

The defaults match `docker-compose.yml` exactly. Edit `.env` only if you have changed credentials or API keys (DrugBank, ICD-11).

#### Demo Language Packs

By default, the API automatically preloads sample language packs from `backend/codex_build/demo_language_packs/` on startup (`LOAD_DEMO_DATA=true`). To start with an empty database (for testing clean manual pack ingestion via UI or CLI), set `LOAD_DEMO_DATA=false` in `.env`.

---

### Step 3 — Install Python dependencies

```bash
pip install -r backend/codex_build/requirements.txt
```

---

### Step 4 — Start the API

```bash
cd backend/codex_build
python api.py
```

Or with auto-reload during development:

```bash
uvicorn api:app --reload
```

Swagger UI is available at [**http://localhost:8000/docs**](http://localhost:8000/docs)

---

### Step 5 — Verify

```bash
cd backend/codex_build
python cli.py
codex> health
```

Expected output:

```
  API   : ✓ running  (v2.0.0)
  Neo4j : ✓ connected
```

---

### Step 6 — Load drug data

Upload CSV files per language/country combination:

```bash
codex> csv upload sample_data/drugs_en_US.csv
codex> csv upload sample_data/drugs_es_MX.csv
```

Verify what was loaded:

```bash
codex> languages          # shows: en, es
codex> countries          # shows: MX (Spanish), US (English)
codex> csv list           # full catalogue sorted alphabetically
```

---

### Step 7 — Translate a drug

```bash
codex> translate
  Drug name (generic or brand): Advil
  Source language code (e.g. en, es, fr): en
  Target language code (e.g. es, uk, fr): es
  Country code (e.g. US, MX) or Enter to search all: MX
```

Returns all matching brand names in the target language, sorted alphabetically:

```
  Brand Name      Generic Name    Original Language   Translated Language
  ──────────────────────────────────────────────────────────────────────
  Advil           Ibuprofeno      English             Spanish
  Anadvil         Ibuprofeno      English             Spanish
```

---

## CSV format

All drug data is managed via CSV files. **One row per (drug, brand, country).**

**Example — English (US):**

```csv
DrugBank ID,Generic Name,Brand Name,Country,Source Language,Language Code
DB00001,Ibuprofen,Advil,US,English,en
DB00001,Ibuprofen,Motrin,US,English,en
DB00002,Acetaminophen,Tylenol,US,English,en
```

**Example — Spanish (MX):**

```csv
DrugBank ID,Generic Name,Brand Name,Country,Source Language,Language Code
DB00001,Ibuprofeno,Advil,MX,Spanish,es
DB00001,Ibuprofeno,Anadvil,MX,Spanish,es
DB00002,Paracetamol,Tempra,MX,Spanish,es
```

The `DrugBank ID` column is the cross-language key used by the API to match terms across languages.

---

## JSON envelope format

All API responses returning tabular data use this envelope:

```json
{
  "metadata": {
    "generated_at":  "<ISO-8601 UTC timestamp>",
    "row_count":     10,
    "source":        "<filename | 'neo4j' | 'translate'>",
    "sort_order":    "generic_name_asc"
  },
  "csv": [ ... ]
}
```

---

## API reference


| Method | Path            | Description                                                |
| ------ | --------------- | ---------------------------------------------------------- |
| GET    | `/health`       | Liveness check — API + Neo4j                               |
| POST   | `/translate`    | Translate a drug name between languages                    |
| GET    | `/audit/{term}` | Quality audit (missing translations / brands)              |
| GET    | `/languages`    | List language codes loaded in Neo4j                        |
| GET    | `/countries`    | List supported countries and their languages               |
| POST   | `/csv/upload`   | Upload a Codex CSV → Neo4j                                 |
| GET    | `/csv`          | Export full drug catalogue (sorted)                        |
| POST   | `/ocrmatching/` | Extract text from image via OCR and fuzzy match drug terms |


### POST /translate — request body

```json
{
  "term":        "Advil",
  "source_lang": "en",
  "target_lang": "es",
  "country":     "MX"
}
```

---

## Database Management &amp; Maintenance

### Changing the Neo4j password

1. Edit `.env`:
   ```
    NEO4J_PASSWORD=your_new_password
   ```
2. Update `docker-compose.yml`:
   ```yaml
    NEO4J_AUTH: "neo4j/your_new_password"
   ```
3. Restart:
   ```bash
    docker compose down && docker compose up -d
   ```

### Stopping or Resetting Neo4j

- **Stop containers (preserve data):**
  ```bash
  docker compose down
  ```
- **Reset and wipe all data:**
  ```bash
  docker compose down -v
  ```

