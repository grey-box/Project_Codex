# Codex — Setup Guide

> **This guide covers the production setup** — no Docker required, everything
> runs locally via `launcher.py`.  
> For Docker-based development and feature testing, see `README.docker.md`.

---

## Prerequisites

| Tool   | Version | Purpose                  |
|--------|---------|--------------------------|
| Python | 3.10+   | API, CLI, and setup script |

That's it. Everything else (Neo4j, JRE, Python packages) is installed automatically by `setup.py`.

---

## Quick start

```
1. python setup.py        # first-time setup — downloads everything
2. python launcher.py     # start the app (Neo4j + API)
3. python cli.py          # open the CLI
```

> **macOS / Linux:** use `python3` in place of `python` above.

---

## Step 1 — Run setup

```bash
python3 setup.py        # macOS / Linux
python setup.py         # Windows
```

This runs once and handles everything:

| What it installs       | Where it goes              |
|------------------------|----------------------------|
| Neo4j Community 5.18   | `runtime/neo4j/`           |
| APOC plugin            | `runtime/neo4j/plugins/`   |
| Eclipse Temurin JRE 17 | `runtime/jre/`             |
| Python dependencies    | your active environment    |

The script detects your OS and CPU architecture automatically and
downloads the correct builds.  It is safe to re-run — anything already
present is skipped.

---

## Step 2 — Start the app

```bash
python3 launcher.py     # macOS / Linux
python launcher.py      # Windows
```

This starts Neo4j and the API silently in the background.  Wait for:

```
✓  Codex ready — http://127.0.0.1:8000
```

**First launch** takes longer (~30s) while Neo4j initialises a fresh
database.  Every subsequent launch is faster (~10–15s).

Your data is stored in the OS app-support directory and is never wiped
between launches or app updates:

| OS      | Data location                          |
|---------|----------------------------------------|
| macOS   | `~/Library/Application Support/Codex/` |
| Windows | `%APPDATA%\Codex\`                     |

---

## Step 3 — Verify

```
codex> health
```

Expected output:
```
  API   : ✓ running  (v2.0.0)
  Neo4j : ✓ connected
```

---

## Step 4 — Load drug data

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

## Step 5 — Translate a drug

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

## Stopping the app

Press `Ctrl+C` in the launcher terminal.  Neo4j will flush and shut down
cleanly — all data is preserved.

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

The `DrugBank ID` column is the cross-language key: the API uses it to
match `Ibuprofen` (English/US) with `Ibuprofeno` (Spanish/MX) when
translating.  Files without a DrugBank ID column still import correctly
but cross-language translation will only work if the canonical names
are identical.

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

Swagger UI is available at **http://localhost:8000/docs** while the launcher is running.

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
