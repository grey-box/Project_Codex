# Codex — Setup Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | API and CLI |
| Docker + Docker Compose | any recent | Neo4j database |
| pip | any | Python dependencies |

---

## Quick start

```
1. docker-compose up -d          # start Neo4j
2. cp .env.example .env          # configure credentials
3. pip install -r requirements.txt
4. python api.py                 # start the API
5. python cli.py                 # open the CLI
```

---

## Step 1 — Start Neo4j

```bash
docker-compose up -d
```

This starts Neo4j 5.18 with the APOC plugin (required for fuzzy matching)
and exposes two ports:

| Port | Use |
|------|-----|
| 7474 | Neo4j Browser — http://localhost:7474 (login: `neo4j` / `changeme`) |
| 7687 | Bolt — used by the API |

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

The defaults match `docker-compose.yml` exactly.  Edit `.env` only if you
have changed the Neo4j credentials.

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

Upload one CSV file per language/country combination:

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

Returns all matching brand names in the target language, sorted
alphabetically:

```
  Brand Name      Generic Name    Original Language   Translated Language
  ──────────────────────────────────────────────────────────────────────
  Advil           Ibuprofeno      English             Spanish
  Anadvil         Ibuprofeno      English             Spanish
```

Both generic names and brand names are valid search inputs:

```
codex> translate → Ibuprofen / en → es   (same result as above)
codex> translate → Ibuprofeno / es → en  (reverse lookup)
```

---

## CSV format

All drug data is managed via CSV files.  **One row per (drug, brand, country).**
Multiple brands for the same drug in the same country = multiple rows.


**Example — English (US):**
```
DrugBank ID,Generic Name,Brand Name,Country,Source Language,Language Code
DB00001,Ibuprofen,Advil,US,English,en
DB00001,Ibuprofen,Motrin,US,English,en
DB00002,Acetaminophen,Tylenol,US,English,en
```

**Example — Spanish (MX):**
```
DrugBank ID,Generic Name,Brand Name,Country,Source Language,Language Code
DB00001,Ibuprofeno,Advil,MX,Spanish,es
DB00001,Ibuprofeno,Anadvil,MX,Spanish,es
DB00002,Paracetamol,Tempra,MX,Spanish,es
```

The `DrugBank ID` column is the cross-language key: the API uses it to match
`Ibuprofen` (English/US) with `Ibuprofeno` (Spanish/MX) when translating.
Files without a DrugBank ID column still import correctly but cross-language
translation will only work if the canonical names are identical.

---

## Adding a new language / country

1. Create a new CSV file following the format above.
2. Upload it:
   ```
   codex> csv upload /path/to/drugs_fr_FR.csv
   ```
3. Verify:
   ```
   codex> countries    # FR should now appear
   codex> languages    # fr should now appear
   ```

---

## JSON envelope format

All API responses that return tabular data use this envelope:

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

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check — API + Neo4j |
| POST | `/translate` | Translate a drug name between languages |
| GET | `/audit/{term}` | Quality audit (missing translations / brands) |
| GET | `/languages` | List language codes loaded in Neo4j |
| GET | `/countries` | List supported countries and their languages |
| POST | `/csv/upload` | Upload a Codex CSV → Neo4j |
| GET | `/csv` | Export full drug catalogue (sorted) |

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

---

## Stopping Neo4j

```bash
docker-compose down          # stop (data is preserved)
docker-compose down -v       # stop and wipe all data
```
