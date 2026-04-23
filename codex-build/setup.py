"""
setup.py — Codex first-time setup (macOS, Linux, Windows)
Run once from the project root:  python setup.py
"""

from __future__ import annotations

import io
import os
import ssl
import sys
import stat
import platform
import shutil
import tarfile
import zipfile
import urllib.request
from pathlib import Path

# ── Versions ──────────────────────────────────────────────────────────────────

NEO4J_VERSION   = "5.18.0"
TEMURIN_VERSION = "17.0.11+9"       # Eclipse Temurin JRE 17
TEMURIN_FILE    = "17.0.11_9"       # same version, + → _ for filenames

# ── Platform detection ────────────────────────────────────────────────────────

OS   = platform.system()   # "Darwin" | "Linux" | "Windows"
ARCH = platform.machine()  # "x86_64" | "arm64" | "AMD64" | "aarch64"

if OS not in ("Darwin", "Linux", "Windows"):
    sys.exit(f"[setup]  Unsupported OS: {OS}")

# Normalise arch to Adoptium naming
if ARCH in ("arm64", "aarch64"):
    CPU = "aarch64"
elif ARCH in ("x86_64", "AMD64"):
    CPU = "x64"
else:
    sys.exit(f"[setup]  Unsupported architecture: {ARCH}")

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).resolve().parent
RUNTIME_DIR = SCRIPT_DIR / "runtime"
NEO4J_DIR   = RUNTIME_DIR / "neo4j"
JRE_DIR     = RUNTIME_DIR / "jre"
TMP_DIR     = RUNTIME_DIR / "_tmp"

# ── Helpers ───────────────────────────────────────────────────────────────────

def info(msg: str)  -> None: print(f"  ✓  {msg}")
def warn(msg: str)  -> None: print(f"  ⚠  {msg}")
def abort(msg: str) -> None: sys.exit(f"\n  ✗  {msg}\n")


def _fetch(url: str, dest: Path, label: str, ctx: ssl.SSLContext | None) -> None:
    """Inner fetch — streams url to dest, showing a progress percentage."""
    req = urllib.request.urlopen(url, context=ctx) if ctx else urllib.request.urlopen(url)
    with req as response:
        total      = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 256  # 256 KB
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  ↓  {label}… {pct}%", end=" ", flush=True)


def download(url: str, dest: Path, label: str) -> None:
    """
    Download url → dest with a progress indicator.

    Tries with full SSL verification first.  If that fails due to a certificate
    error (common on macOS where Python's cert bundle is not linked to the
    system keychain), retries with verification disabled and prints a warning.
    The downloads are well-known release artifacts from trusted sources so this
    is acceptable for a setup script.
    """
    print(f"  ↓  {label}…", end=" ", flush=True)
    try:
        _fetch(url, dest, label, ctx=None)
        print(f"\r  ✓  {label} downloaded       ")
    except urllib.error.URLError as exc:
        # Catch SSL certificate errors specifically and retry without verification
        if "CERTIFICATE_VERIFY_FAILED" in str(exc) or "SSL" in str(exc).upper():
            print(f"\r  ⚠  SSL certificate check failed — retrying without verification…")
            warn(
                "SSL verification disabled for this download.\n"
                "     To fix permanently on macOS, run:\n"
                "     /Applications/Python\\ 3.x/Install\\ Certificates.command"
            )
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode    = ssl.CERT_NONE
                _fetch(url, dest, label, ctx=ctx)
                print(f"\r  ✓  {label} downloaded       ")
            except Exception as exc2:
                print()
                abort(f"Download failed: {exc2}\n     URL: {url}")
        else:
            print()
            abort(f"Download failed: {exc}\n     URL: {url}")


def extract_tar(archive: Path, dest: Path) -> None:
    print(f"  ⟳  Extracting {archive.name}…", end=" ", flush=True)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(dest)
    print("done")


def extract_zip(archive: Path, dest: Path) -> None:
    print(f"  ⟳  Extracting {archive.name}…", end=" ", flush=True)
    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(dest)
    print("done")


def find_extracted(parent: Path, prefix: str) -> Path | None:
    """Find the first subdirectory whose name starts with prefix."""
    for p in parent.iterdir():
        if p.is_dir() and p.name.startswith(prefix):
            return p
    return None


def make_executable(path: Path) -> None:
    """Set executable bit on a file (no-op on Windows)."""
    if OS != "Windows":
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# ── Setup steps ───────────────────────────────────────────────────────────────

def setup_neo4j() -> None:
    if NEO4J_DIR.exists():
        warn("Neo4j already present at runtime/neo4j — skipping")
        return

    TMP_DIR.mkdir(parents=True, exist_ok=True)

    if OS == "Windows":
        archive  = TMP_DIR / "neo4j.zip"
        url      = f"https://dist.neo4j.org/neo4j-community-{NEO4J_VERSION}-windows.zip"
        download(url, archive, f"Neo4j Community {NEO4J_VERSION}")
        extract_zip(archive, TMP_DIR)
    else:
        archive  = TMP_DIR / "neo4j.tar.gz"
        url      = f"https://dist.neo4j.org/neo4j-community-{NEO4J_VERSION}-unix.tar.gz"
        download(url, archive, f"Neo4j Community {NEO4J_VERSION}")
        extract_tar(archive, TMP_DIR)

    extracted = find_extracted(TMP_DIR, "neo4j-community-")
    if not extracted:
        abort("Could not locate extracted Neo4j folder.")

    shutil.move(str(extracted), NEO4J_DIR)
    archive.unlink(missing_ok=True)
    info("Neo4j ready at runtime/neo4j")


def setup_apoc() -> None:
    apoc_jar = NEO4J_DIR / "plugins" / f"apoc-{NEO4J_VERSION}-core.jar"

    if apoc_jar.exists():
        warn("APOC plugin already present — skipping")
        return

    (NEO4J_DIR / "plugins").mkdir(exist_ok=True)
    url = (
        f"https://github.com/neo4j/apoc/releases/download/"
        f"{NEO4J_VERSION}/apoc-{NEO4J_VERSION}-core.jar"
    )
    try:
        download(url, apoc_jar, "APOC plugin")
        info("APOC plugin ready")
    except SystemExit:
        warn("APOC download failed — add it manually later (see BUNDLE_SETUP.md)")


def setup_jre() -> None:
    if JRE_DIR.exists():
        warn("JRE already present at runtime/jre — skipping")
        return

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"jdk-{TEMURIN_VERSION}"

    if OS == "Windows":
        filename = f"OpenJDK17U-jre_{CPU}_windows_hotspot_{TEMURIN_FILE}.zip"
        archive  = TMP_DIR / "jre.zip"
        url      = f"https://github.com/adoptium/temurin17-binaries/releases/download/{tag}/{filename}"
        download(url, archive, f"Eclipse Temurin JRE 17 ({CPU})")
        extract_zip(archive, TMP_DIR)
    elif OS == "Darwin":
        filename = f"OpenJDK17U-jre_{CPU}_mac_hotspot_{TEMURIN_FILE}.tar.gz"
        archive  = TMP_DIR / "jre.tar.gz"
        url      = f"https://github.com/adoptium/temurin17-binaries/releases/download/{tag}/{filename}"
        download(url, archive, f"Eclipse Temurin JRE 17 ({CPU})")
        extract_tar(archive, TMP_DIR)
    else:  # Linux
        filename = f"OpenJDK17U-jre_{CPU}_linux_hotspot_{TEMURIN_FILE}.tar.gz"
        archive  = TMP_DIR / "jre.tar.gz"
        url      = f"https://github.com/adoptium/temurin17-binaries/releases/download/{tag}/{filename}"
        download(url, archive, f"Eclipse Temurin JRE 17 ({CPU})")
        extract_tar(archive, TMP_DIR)

    # Adoptium extracts to a versioned folder — find and rename it
    extracted = find_extracted(TMP_DIR, "jdk-")
    if not extracted:
        # Some builds use a different prefix — grab whatever's left
        candidates = [p for p in TMP_DIR.iterdir() if p.is_dir() and p.name != "_tmp"]
        extracted  = candidates[0] if candidates else None
    if not extracted:
        abort("Could not locate extracted JRE folder. Rename it to runtime/jre manually.")

    # macOS Temurin archives nest the JRE under Contents/Home
    mac_home = extracted / "Contents" / "Home"
    if OS == "Darwin" and mac_home.exists():
        extracted = mac_home

    shutil.move(str(extracted), JRE_DIR)
    archive.unlink(missing_ok=True)

    # Ensure java binary is executable
    java_bin = JRE_DIR / "bin" / ("java.exe" if OS == "Windows" else "java")
    if java_bin.exists():
        make_executable(java_bin)

    info("JRE ready at runtime/jre")


def setup_python_deps() -> None:
    requirements = SCRIPT_DIR / "requirements.txt"
    if not requirements.exists():
        warn("requirements.txt not found — skipping pip install")
        return

    print("  ↓  Installing Python dependencies…", end=" ", flush=True)
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements), "--quiet"],
        capture_output=True,
    )
    if result.returncode != 0:
        print()
        abort(f"pip install failed:\n{result.stderr.decode()}")
    print("done")
    info("Python dependencies installed")


def cleanup() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR, ignore_errors=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print(f"  Codex setup  —  {OS} / {CPU}")
    print(f"  {'─' * 40}")

    try:
        setup_neo4j()
        setup_apoc()
        setup_jre()
        setup_python_deps()
    finally:
        cleanup()

    print()
    print("  ✓  Setup complete")
    print()
    if OS == "Windows":
        print("     Start the app:   python launcher.py")
        print("     Open the CLI:    python cli.py")
    else:
        print("     Start the app:   python3 launcher.py")
        print("     Open the CLI:    python3 cli.py")
    print()


if __name__ == "__main__":
    main()
