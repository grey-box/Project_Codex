#!/usr/bin/env python3
"""
Codex CLI
=========
Terminal interface for the Codex Translation API.

Every command makes an HTTP request to the FastAPI service.
No direct database or backend imports — the API is the only entry point.

Flow:  CLI  →  HTTP  →  FastAPI (api.py)  →  codex backend  →  Neo4j

Start the API first:
    python api.py          (or: uvicorn api:app --reload)
Then run this:
    python cli.py
"""

import sys
import os

try:
    import httpx
except ImportError:
    print("Missing dependency: run  pip3 install httpx")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = os.getenv("CODEX_API_URL", "http://localhost:8000")
TIMEOUT  = 15

# ── Colour helpers ────────────────────────────────────────────────────────────
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def bold(s):   return f"{BOLD}{s}{RESET}"
def green(s):  return f"{GREEN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _request(method: str, path: str, **kwargs):
    """
    Make an HTTP request to the API.
    Prints the method + path + status code on every call so you can see
    exactly what is happening at the HTTP layer.
    Returns the parsed JSON body, or None on error.
    """
    try:
        with httpx.Client(base_url=API_BASE, timeout=TIMEOUT) as client:
            resp = getattr(client, method)(path, **kwargs)

        status_color = green if resp.status_code < 300 else (
            yellow if resp.status_code < 500 else red
        )
        print(dim(f"  {method.upper()} {API_BASE}{path}  →  {status_color(str(resp.status_code))}"))

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            print(red(f"  ✗  {detail}"))
            return None

        return resp.json()

    except httpx.ConnectError:
        print(red(f"\n  ✗  Cannot connect to API at {API_BASE}"))
        print(f"     Start the API first:  {cyan('python api.py')}\n")
        return None
    except httpx.TimeoutException:
        print(red("  ✗  Request timed out"))
        return None


# ── Display helpers ───────────────────────────────────────────────────────────

def _print_translation(data: dict):
    print()
    print(bold(f"  Canonical      : {data['canonical']}"))
    print(f"  Requested lang : {data.get('requested_language') or '(none)'}")
    print(f"  Used lang      : {data.get('used_language') or '—'}")

    if data.get("fallback_used"):
        fb_type  = data.get("fallback_type", "unknown")
        fb_chain = " → ".join(data.get("fallback_chain") or [])
        print(yellow(f"  ⚠  Fallback ({fb_type}): {fb_chain}"))
    else:
        print(green("  ✓  Direct match — no fallback needed"))

    results = data.get("results", [])
    if not results:
        if data.get("missing_language_pack"):
            print(red("  ✗  Language pack not loaded"))
            print(f"     Use {cyan('load <path>')} to add it, or {cyan('demo')} for sample data.")
        else:
            print(red("  ✗  No translations found"))
        print()
        return

    print(bold("\n  Results:"))
    for r in results:
        brand   = f"  brand: {r['brand']}" if r.get("brand") else ""
        country = f"  [{r['country']}]"     if r.get("country") else ""
        print(f"    • {green(r['translation'])}  ({r['language']}){brand}{country}")
    print()


def _print_audit(data: dict):
    print()
    print(bold(f"  Canonical : {data['canonical']}"))

    mt = data.get("missing_translations", [])
    if mt:
        print(yellow(f"\n  Missing translations ({len(mt)} countries):"))
        for m in mt:
            print(f"    • {m['country']}  {dim(m['country_name'])}")
    else:
        print(green("\n  ✓  Translations present for all known countries"))

    mb = data.get("missing_brands", [])
    if mb:
        print(yellow(f"\n  Missing brand names ({len(mb)} countries):"))
        for m in mb:
            print(f"    • {m['country']}  {dim(m['country_name'])}")
    else:
        print(green("  ✓  Brand names present for all known countries"))

    eq = data.get("equivalent_brands", [])
    if eq:
        print(bold("\n  Equivalent brands across countries:"))
        for e in eq:
            print(f"    • {e['brand']}  [{e['country']} / {dim(e['country_name'])}]")
    print()


def _print_help():
    print(f"""
  {bold('Commands')}
    {cyan('<drug name>')}     Translate a term  (prompts for language + country)
    {cyan('audit <term>')}    Quality audit — missing translations / brands
    {cyan('demo')}            Load built-in sample data
    {cyan('load <path>')}     Upload a language pack JSON
    {cyan('languages')}       List languages loaded in Neo4j
    {cyan('health')}          Check API + Neo4j connection
    {cyan('help')}            Show this message
    {cyan('quit')}            Exit

  {bold('Swagger UI')}  {dim(API_BASE + '/docs')}
""")


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {label}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return val if val else default


# ── Command handlers ──────────────────────────────────────────────────────────

def cmd_health():
    data = _request("get", "/health")
    if not data:
        return
    neo4j_status = green("✓ connected") if data["neo4j"] else red("✗ unreachable")
    print(f"\n  API    : {green('✓ running')}  (v{data['api_version']})")
    print(f"  Neo4j  : {neo4j_status}\n")


def cmd_languages():
    data = _request("get", "/languages")
    if not data:
        return
    langs = data.get("languages", [])
    if langs:
        print(f"\n  Loaded: {', '.join(langs)}\n")
    else:
        print(yellow("\n  No languages loaded yet — run 'demo' first.\n"))


def cmd_demo():
    print("  Loading sample data…")
    data = _request("post", "/demo/load")
    if data:
        print(green(f"  ✓  {data['message']}\n"))


def cmd_load(path: str):
    if not path:
        print(red("  ✗  Provide a path:  load /path/to/pack.json"))
        return
    if not os.path.exists(path):
        print(red(f"  ✗  File not found: {path}"))
        return
    print(f"  Uploading {os.path.basename(path)}…")
    with open(path, "rb") as f:
        data = _request(
            "post", "/packs/load",
            files={"file": (os.path.basename(path), f, "application/json")},
        )
    if data:
        print(green(f"  ✓  {data['message']}\n"))


def cmd_translate(term: str):
    lang    = _prompt("Target language (en/es/fr/ru/uk) or Enter to skip")
    country = _prompt("Country code (US/GB/MX/…)  or Enter to skip")

    payload = {"term": term}
    if lang:    payload["lang"]    = lang
    if country: payload["country"] = country

    data = _request("post", "/translate", json=payload)
    if data:
        _print_translation(data)


def cmd_audit(term: str):
    if not term:
        print(red("  ✗  Provide a term:  audit ibuprofen"))
        return
    data = _request("get", f"/audit/{term}")
    if data:
        _print_audit(data)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print(bold("\nCodex Medical Translation — CLI"))
    print(f"  API  : {cyan(API_BASE)}")
    print(f"  Docs : {cyan(API_BASE + '/docs')}")
    print(f"  Type {cyan('health')} to verify connection, {cyan('help')} for all commands.\n")

    while True:
        try:
            raw = input(bold("codex> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not raw:
            continue

        lower = raw.lower()

        if lower in ("quit", "exit", "q"):
            print("Bye.")
            break
        elif lower in ("help", "?"):
            _print_help()
        elif lower == "health":
            cmd_health()
        elif lower == "languages":
            cmd_languages()
        elif lower == "demo":
            cmd_demo()
        elif lower.startswith("load"):
            parts = raw.split(None, 1)
            path = parts[1] if len(parts) > 1 else _prompt("Path to language pack JSON")
            cmd_load(path)
        elif lower.startswith("audit"):
            parts = raw.split(None, 1)
            term = parts[1] if len(parts) > 1 else _prompt("Term to audit")
            cmd_audit(term.strip())
        else:
            cmd_translate(raw)


if __name__ == "__main__":
    main()
