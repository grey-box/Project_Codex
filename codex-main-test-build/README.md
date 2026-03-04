# codex-cli — Medical Translation Terminal

Test the backend translation engine directly from your terminal.
No frontend, no Flask, no middleware. Just Neo4j + Python.

---

## Setup (once)

### 1 — Start Neo4j
```bash
docker compose up -d
# Wait ~20 seconds for Neo4j to be ready
# Optional: check http://localhost:7474 in a browser (login: neo4j / changeme)
```

### 2 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3 — Run the CLI
```bash
python cli.py
```

---

## Usage

```
codex> demo                    ← load sample data first (run this once)
codex> ibuprofen               ← type a drug name, then answer prompts
  Target language code: es
  Country code: MX
  → ibuprofeno  (Spanish)  brand: Advil  [MX]

codex> paracetamol
  Target language code: fr
  Country code: FR
  → paracétamol  (French)  brand: Doliprane  [FR]

codex> audit ibuprofen         ← show missing translations / brands
codex> load /path/to/pack.json ← load a new language pack
codex> quit
```

### Language codes
Code - Language

`en` - English 
`es` - Spanish 
`fr` - French 
`ru` - Russian 
`uk` - Ukrainian 

### Country codes
`US  GB  MX  FR  ES  NG  RU  UA  CA  PL  IN  DE  BR  AU  ZA`

---

## Language pack format

```json
{
  "language": {"code": "pt", "name": "Portuguese"},
  "terms": [
    {
      "canonical": "Ibuprofen",
      "entries": [
        {"translation": "ibuprofeno", "country": "BR", "brand": "Advil"},
        {"translation": "ibuprofeno", "country": "PT", "brand": null}
      ]
    }
  ]
}
```

Save as `portuguese_pack.json`, then:
```bash
codex> load portuguese_pack.json
```

---

## Changing the Neo4j password

Edit `.env`:
```
NEO4J_PASSWORD=your_new_password
```

And update `docker-compose.yml`:
```yaml
NEO4J_AUTH: "neo4j/your_new_password"
```

Then restart: `docker compose down && docker compose up -d`

---

## Resetting the database

```bash
docker compose down -v    # -v removes the data volume
docker compose up -d
# Then reload demo data:  codex> demo
```
