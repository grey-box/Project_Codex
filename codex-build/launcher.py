"""
launcher.py — Codex application orchestrator
=============================================
Starts Neo4j (bundled) and the FastAPI server silently on app boot.
Shuts both down cleanly when the app closes.
Data persists across launches — the Neo4j data directory is never wiped.

Expected bundle layout (relative to this file):
    runtime/
        neo4j/          ← extracted Neo4j Community Server 5.18
        jre/            ← bundled JRE 17+

Persistent data is stored in the OS-appropriate app-support directory:
    macOS   ~/Library/Application Support/Codex/
    Windows %APPDATA%/Codex/
"""

from __future__ import annotations

import os
import sys
import time
import signal
import socket
import logging
import platform
import subprocess
import threading
from pathlib import Path


# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("codex.launcher")


# ── Platform ───────────────────────────────────────────────────────────────────

IS_WINDOWS = platform.system() == "Windows"
IS_MAC     = platform.system() == "Darwin"

# Silence subprocess windows on Windows
_WIN_FLAGS = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0


# ── Paths ──────────────────────────────────────────────────────────────────────

# Root of the application bundle (directory containing this file)
APP_ROOT = Path(__file__).resolve().parent

# Bundled runtimes — ship these inside the app package
RUNTIME_DIR = APP_ROOT / "runtime"
NEO4J_HOME  = RUNTIME_DIR / "neo4j"
JRE_HOME    = RUNTIME_DIR / "jre"

# Persistent data directory — survives every relaunch, never auto-deleted
if IS_WINDOWS:
    _appdata = Path(os.environ.get("APPDATA", Path.home()))
elif IS_MAC:
    _appdata = Path.home() / "Library" / "Application Support"
else:
    _appdata = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

DATA_ROOT      = _appdata / "Codex"
NEO4J_DATA_DIR = DATA_ROOT / "neo4j-data"
NEO4J_LOGS_DIR = DATA_ROOT / "neo4j-logs"
NEO4J_CONF_DIR = DATA_ROOT / "neo4j-conf"

# Ports
NEO4J_BOLT_PORT = 7687
NEO4J_HTTP_PORT = 7474
API_PORT        = int(os.environ.get("API_PORT", 8000))


# ── Process handles ────────────────────────────────────────────────────────────

_neo4j_proc:    subprocess.Popen | None = None
_api_proc:      subprocess.Popen | None = None
_shutdown_event = threading.Event()


# ── Helpers ────────────────────────────────────────────────────────────────────

def port_open(port: int) -> bool:
    """Return True if something is already accepting connections on this port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_port(port: int, timeout: int, label: str) -> bool:
    """
    Poll a TCP port every second until it accepts a connection.
    Returns True on success, False on timeout.
    """
    log.info("Waiting for %s (port %d, up to %ds)…", label, port, timeout)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_open(port):
            log.info("%s is ready", label)
            return True
        time.sleep(1)
    log.error("%s did not become ready within %ds", label, timeout)
    return False


def _neo4j_env() -> dict[str, str]:
    """Build the environment block for all Neo4j subprocess calls."""
    env = os.environ.copy()
    env["NEO4J_HOME"] = str(NEO4J_HOME)
    env["NEO4J_CONF"] = str(NEO4J_CONF_DIR)
    env["JAVA_HOME"]  = str(JRE_HOME)
    # Prepend bundled JRE bin so Neo4j scripts find `java` without relying on
    # whatever (if anything) the user has installed system-wide.
    jre_bin = str(JRE_HOME / "bin")
    env["PATH"] = jre_bin + os.pathsep + env.get("PATH", "")
    return env


# ── Neo4j config ───────────────────────────────────────────────────────────────

def _write_neo4j_conf() -> None:
    """
    Write a minimal neo4j.conf into the persistent config directory.
    Only recreated on first run or if the file is missing — existing data is
    always preserved because we never touch NEO4J_DATA_DIR itself.
    """
    NEO4J_DATA_DIR.mkdir(parents=True, exist_ok=True)
    NEO4J_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    NEO4J_CONF_DIR.mkdir(parents=True, exist_ok=True)

    conf_file = NEO4J_CONF_DIR / "neo4j.conf"
    if conf_file.exists():
        return  # Never overwrite — would discard any manual tuning

    # Forward-slash paths are safe on all platforms for Neo4j config values
    data = NEO4J_DATA_DIR.as_posix()
    logs = NEO4J_LOGS_DIR.as_posix()

    conf_file.write_text(
        f"# Codex — auto-generated on first launch (safe to edit)\n"
        f"server.directories.data={data}\n"
        f"server.directories.logs={logs}\n"
        f"server.bolt.listen_address=127.0.0.1:{NEO4J_BOLT_PORT}\n"
        f"server.http.listen_address=127.0.0.1:{NEO4J_HTTP_PORT}\n"
        f"dbms.security.auth_enabled=true\n"
        # Constrain heap — a local app doesn't need the default 512 m / 1 g
        f"server.jvm.additional=-Xms128m\n"
        f"server.jvm.additional=-Xmx512m\n",
        encoding="utf-8",
    )
    log.info("Neo4j config written to %s", conf_file)


# ── Neo4j lifecycle ────────────────────────────────────────────────────────────

def _set_initial_password() -> None:
    """
    Run neo4j-admin to set the initial password on a brand-new database.

    Neo4j 5.x requires this before first start — without it the server starts
    but rejects all Bolt connections because no credentials have been
    provisioned.  The Docker image handled this via NEO4J_AUTH; bare installs
    must do it explicitly.

    Skipped on every subsequent launch because the data directory already
    exists and the password is already set inside the store.
    """
    # Use the databases subdirectory as an initialisation marker —
    # it is created by neo4j-admin during set-initial-password.
    marker = NEO4J_DATA_DIR / "databases"
    if marker.exists():
        return

    password = os.getenv("NEO4J_PASSWORD", "changeme")
    log.info("Setting Neo4j initial password...")

    env = _neo4j_env()

    if IS_WINDOWS:
        admin_bin = NEO4J_HOME / "bin" / "neo4j-admin.bat"
        cmd = ["cmd", "/c", str(admin_bin),
               "dbms", "set-initial-password", password]
    else:
        admin_bin = NEO4J_HOME / "bin" / "neo4j-admin"
        admin_bin.chmod(admin_bin.stat().st_mode | 0o111)
        cmd = [str(admin_bin), "dbms", "set-initial-password", password]

    result = subprocess.run(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        err = result.stderr.decode().strip()
        log.warning("neo4j-admin set-initial-password returned non-zero: %s", err)
    else:
        log.info("Neo4j initial password set")


def start_neo4j() -> bool:
    global _neo4j_proc

    if port_open(NEO4J_BOLT_PORT):
        log.info("Neo4j already running on port %d — skipping start", NEO4J_BOLT_PORT)
        return True

    _write_neo4j_conf()
    _set_initial_password()
    env = _neo4j_env()

    # `neo4j console` runs Neo4j in the foreground so we keep a live process
    # handle and can terminate it cleanly.  On Windows we must invoke the
    # batch file via cmd /c.
    if IS_WINDOWS:
        neo4j_bat = NEO4J_HOME / "bin" / "neo4j.bat"
        cmd = ["cmd", "/c", str(neo4j_bat), "console"]
    else:
        neo4j_bin = NEO4J_HOME / "bin" / "neo4j"
        neo4j_bin.chmod(neo4j_bin.stat().st_mode | 0o111)  # ensure executable
        cmd = [str(neo4j_bin), "console"]

    log.info("Starting Neo4j…")
    _neo4j_proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_WIN_FLAGS,
    )

    # Neo4j 5.x is slow to initialise on first boot (JVM + store creation).
    # Give it up to 120 s; subsequent boots are typically 10–20 s.
    return wait_for_port(NEO4J_BOLT_PORT, timeout=120, label="Neo4j")


def stop_neo4j() -> None:
    global _neo4j_proc
    if _neo4j_proc is None:
        return

    log.info("Stopping Neo4j…")

    if IS_WINDOWS:
        # Use the stop script for a clean JVM shutdown on Windows
        stop_bat = NEO4J_HOME / "bin" / "neo4j.bat"
        subprocess.run(
            ["cmd", "/c", str(stop_bat), "stop"],
            env=_neo4j_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_WIN_FLAGS,
        )
    else:
        # SIGTERM triggers Neo4j's JVM shutdown hook — data is flushed safely
        _neo4j_proc.terminate()

    try:
        _neo4j_proc.wait(timeout=30)
        log.info("Neo4j stopped cleanly")
    except subprocess.TimeoutExpired:
        log.warning("Neo4j shutdown timed out — forcing kill")
        _neo4j_proc.kill()
        _neo4j_proc.wait()

    _neo4j_proc = None


# ── API lifecycle ──────────────────────────────────────────────────────────────

def start_api() -> bool:
    global _api_proc

    cmd = [
        sys.executable, "-m", "uvicorn",
        "api:app",
        "--host", "127.0.0.1",
        "--port", str(API_PORT),
        "--log-level", "warning",
    ]

    log.info("Starting Codex API on port %d…", API_PORT)
    _api_proc = subprocess.Popen(
        cmd,
        cwd=str(APP_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=None,   # let API stderr print to launcher terminal for debugging
        creationflags=_WIN_FLAGS,
    )

    return wait_for_port(API_PORT, timeout=30, label="Codex API")


def stop_api() -> None:
    global _api_proc
    if _api_proc is None:
        return

    log.info("Stopping API…")
    _api_proc.terminate()
    try:
        _api_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _api_proc.kill()
        _api_proc.wait()
    _api_proc = None
    log.info("API stopped")


# ── Shutdown ───────────────────────────────────────────────────────────────────

def shutdown(signum=None, frame=None) -> None:
    """
    Graceful shutdown — called on SIGTERM, SIGINT, or when the API process
    exits unexpectedly.  Safe to call multiple times (idempotent).
    """
    if _shutdown_event.is_set():
        return
    _shutdown_event.set()
    log.info("Shutdown initiated")
    stop_api()
    stop_neo4j()
    log.info("Codex shut down cleanly — goodbye")
    sys.exit(0)


# Register OS-level signal handlers.
# The frontend wrapper (Electron/Tauri) should send SIGTERM to this process
# when the user closes the window.  Alternatively it can POST /shutdown to
# the API, which terminates uvicorn; the monitor loop below detects that and
# calls shutdown() automatically.
signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT,  shutdown)


# ── Startup validation ─────────────────────────────────────────────────────────

def _validate_bundle() -> None:
    missing = []
    if not NEO4J_HOME.exists():
        missing.append(f"Neo4j bundle:  {NEO4J_HOME}")
    if not JRE_HOME.exists():
        missing.append(f"JRE bundle:    {JRE_HOME}")

    if missing:
        for m in missing:
            log.critical("Missing bundle component — %s", m)
        log.critical(
            "See BUNDLE_SETUP.md for instructions on adding runtime dependencies."
        )
        sys.exit(1)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Codex launcher starting (pid %d)", os.getpid())
    _validate_bundle()

    if not start_neo4j():
        log.critical("Neo4j failed to start — aborting")
        sys.exit(1)

    if not start_api():
        log.critical("API failed to start — aborting")
        stop_neo4j()
        sys.exit(1)

    log.info("✓  Codex ready — http://127.0.0.1:%d", API_PORT)

    # ── FRONTEND INTEGRATION POINT ────────────────────────────────────────
    # Signal to your Electron / Tauri shell that the backend is ready and the
    # loading screen can be dismissed.
    #
    # Option A (Electron — recommended):
    #   In your Electron main process, spawn launcher.py as a child process.
    #   Watch its stdout for the line containing "Codex ready".
    #   When found, call mainWindow.loadURL('http://127.0.0.1:8000') or
    #   show the window.
    #
    # Option B (Tauri):
    #   Use tauri::api::process::Command to spawn launcher.py.
    #   Listen for the same stdout signal.
    #
    # Option C (either — frontend-driven):
    #   Show a loading screen immediately on launch.
    #   Poll GET /health every second until {"neo4j": true} is returned,
    #   then dismiss the loading screen.  No IPC needed.
    # ─────────────────────────────────────────────────────────────────────
    print("CODEX_READY", flush=True)  # machine-readable signal for Options A/B

    # Monitor loop — keep the launcher alive and watch for unexpected exits
    while not _shutdown_event.is_set():
        if _api_proc and _api_proc.poll() is not None:
            # The API exited on its own (e.g. POST /shutdown was called by
            # the frontend).  That's the cue to shut everything else down.
            log.info("API process exited — beginning full shutdown")
            shutdown()
            break
        time.sleep(2)


if __name__ == "__main__":
    main()
