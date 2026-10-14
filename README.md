# Codex — Setup Guide

---

## Quick start

```bash
docker compose up --build
# Wait ~30 seconds for Neo4j, frontend, and api to be ready
# Optional: check http://localhost:7474 in a browser (login: neo4j / changeme)
```

---

## Step 6 — Load drug data

Upload one CSV file per language/country combination:

```
Use http://localhost:9000 for the frontend
NOTE: It will choose a free host port from 9000 through 9010. 
If http://localhost:9000 does not work, try any of the other ports.
Use http://localhost:7474 for the Neo4j backend
Use http://localhost:8000/docs to view the API
```

`term` accepts both generic names (`Ibuprofen`) and brand names (`Advil`).
`country` is optional — omit it to return results across all countries.

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

Then restart: `docker compose down && docker compose up -d && docker compose up --build`

---

## Resetting the database

```bash
docker compose down -v    # -v removes the data volume
docker compose up -d
docker compose up --build
```
