# Codex — Bundle Setup Guide

How to assemble the final distributable app from the project source.

---

## Final directory structure

```
codex-app/
├── launcher.py               ← orchestrator (start here)
├── api.py                    ← FastAPI backend (unchanged)
├── cli.py
├── codex/
│   ├── neo4j_driver.py
│   └── services/
├── sample_data/
├── requirements.txt
├── .env                      ← generated at first launch (see below)
│
├── runtime/                  ← YOU MUST ADD THIS (not in source repo)
│   ├── neo4j/                ← extracted Neo4j Community 5.18
│   └── jre/                  ← extracted JRE 17+
│
└── frontend/                 ← built by the frontend team (Vite output)
    └── dist/
        ├── index.html
        └── assets/
```

Data is stored separately from the app bundle and survives updates:

| OS      | Path                                              |
|---------|---------------------------------------------------|
| macOS   | `~/Library/Application Support/Codex/`            |
| Windows | `%APPDATA%\Codex\`                                |

---

## Step 1 — Download Neo4j Community Server 5.18

**macOS / Linux**
```bash
# Download
curl -L https://dist.neo4j.org/neo4j-community-5.18.0-unix.tar.gz \
     -o neo4j.tar.gz

# Extract and rename
tar -xzf neo4j.tar.gz
mv neo4j-community-5.18.0 runtime/neo4j
```

**Windows**
```
Download: https://neo4j.com/artifact.php?name=neo4j-community-5.18.0-windows.zip
Extract the zip, rename the folder to `runtime\neo4j`
```

### Add the APOC plugin (required)

```bash
# Download APOC 5.18.x core jar from:
# https://github.com/neo4j/apoc/releases

# Place it in:
runtime/neo4j/plugins/apoc-5.18.x-core.jar
```

Add these two lines to `runtime/neo4j/conf/neo4j.conf`
(the launcher will write its own conf to the data dir — this is the
 base conf that ships inside the bundle):

```
dbms.security.procedures.unrestricted=apoc.*
server.directories.plugins=<absolute path to runtime/neo4j/plugins>
```

---

## Step 2 — Bundle a JRE

Neo4j 5.x requires Java 17.  You need a JRE that matches the target OS
and CPU architecture.

**Recommended source: Eclipse Temurin (free, no licence headaches)**
https://adoptium.net/temurin/releases/?version=17

Download the JRE (not JDK) archive for your target platform, extract it,
and rename the root folder to `runtime/jre`.

| Target         | Archive type | Rename to        |
|----------------|--------------|------------------|
| macOS (arm64)  | .tar.gz      | `runtime/jre`    |
| macOS (x64)    | .tar.gz      | `runtime/jre`    |
| Windows (x64)  | .zip         | `runtime\jre`    |

> **Cross-platform builds:** you need separate app bundles per OS — the
> JRE and Neo4j binaries are platform-specific.  Build the macOS bundle
> on a Mac and the Windows bundle on Windows (or use CI runners).

---

## Step 3 — Configure .env

The launcher writes `.env` automatically on first run with sane defaults.
If you want to pre-seed it for the packaged build, create `.env` in
`APP_ROOT` with:

```
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
API_PORT=8000
```

---

## Step 4 — Python environment

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

When packaging with **PyInstaller**, point it at `launcher.py` as the
entry point and include the `codex/` package and `runtime/` directory
as data files.  Example spec snippet:

```python
a = Analysis(
    ['launcher.py'],
    datas=[
        ('codex',   'codex'),
        ('runtime', 'runtime'),
        ('api.py',  '.'),
        ('.env',    '.'),
    ],
    ...
)
```

---

## Step 5 — Frontend integration

The frontend team needs to implement two things:

### A — Loading screen (required)

On startup, show a loading screen while the backend initialises.
Poll `GET http://127.0.0.1:8000/health` every second.
When the response contains `"neo4j": true`, dismiss the loading screen.

```typescript
// Example polling helper (framework-agnostic)
async function waitForBackend(maxWaitMs = 90_000): Promise<void> {
  const interval = 1000;
  const deadline = Date.now() + maxWaitMs;

  while (Date.now() < deadline) {
    try {
      const res  = await fetch("http://127.0.0.1:8000/health");
      const body = await res.json();
      if (body.neo4j === true) return;   // ✓ backend is ready
    } catch {
      // API not up yet — keep polling
    }
    await new Promise(r => setTimeout(r, interval));
  }
  throw new Error("Backend did not become ready in time");
}
```

### B — Shutdown on window close (required)

When the user closes the app window, call `POST /shutdown` **before**
terminating the desktop wrapper process.  This gives Neo4j time to
flush and close its store cleanly.

```typescript
// Electron — in main process, before app.quit()
async function shutdownBackend(): Promise<void> {
  try {
    await fetch("http://127.0.0.1:8000/shutdown", { method: "POST" });
    await new Promise(r => setTimeout(r, 1000)); // give launcher time to exit
  } catch {
    // API may already be down — that's fine
  }
}

app.on("before-quit", async (event) => {
  event.preventDefault();
  await shutdownBackend();
  app.exit(0);
});
```

```typescript
// Tauri — in your Rust backend, before the window closes
// Emit a shutdown event that your TypeScript side catches:
// window.__TAURI__.event.listen("tauri://close-requested", async () => {
//   await fetch("http://127.0.0.1:8000/shutdown", { method: "POST" });
// });
```

---

## First-launch behaviour

| Event                             | What happens                              |
|-----------------------------------|-------------------------------------------|
| Very first launch                 | Neo4j creates its store (~20s extra)      |
| Every subsequent launch           | Neo4j opens existing store (~10–15s)      |
| App closes normally               | Neo4j flushes and shuts down — data safe  |
| App force-killed (crash)          | Neo4j runs recovery on next boot (~5s)    |
| App updated (bundle replaced)     | Data directory untouched — no data loss   |
| User uninstalls                   | Data directory is NOT removed (by design) |

---

## Adding the `/shutdown` endpoint to api.py

Merge the contents of `shutdown_endpoint.py` into `api.py`:

1. Add `import threading` to the existing imports at the top.
2. Add the `ShutdownResponse` Pydantic model with the other models.
3. Add the `POST /shutdown` route with the other routes.

The full snippet is in `shutdown_endpoint.py`.
