#!/usr/bin/env python3
"""
Codex CLI
Terminal interface for the Codex Translation API.

Every command makes one HTTP request to the FastAPI service.
No direct database imports — the API is the sole entry point.

Flow:  CLI  ->  HTTP  ->  FastAPI (api.py)  ->  Neo4j

Start the API first:
    python api.py
Then run:
    python cli.py
"""

import sys
import os

try:
    import httpx
except ImportError:
    print("Missing dependency: pip install httpx")
    sys.exit(1)

API_BASE = os.getenv("CODEX_API_URL", "http://localhost:8000")
TIMEOUT  = 15

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


#HTTP helpers

def _request(method: str, path: str, **kwargs):
    try:
        with httpx.Client(base_url=API_BASE, timeout=TIMEOUT) as client:
            resp = getattr(client, method)(path, **kwargs)

        sc = green if resp.status_code < 300 else (
             yellow if resp.status_code < 500 else red)
        print(dim(f"  {method.upper()} {API_BASE}{path}  →  {sc(str(resp.status_code))}"))

        if resp.status_code >= 400:
            try:   detail = resp.json().get("detail", resp.text)
            except Exception: detail = resp.text
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


# Display helpers

def _col_width(rows, key, header, max_w):
    """Calculate column width: max of header and data, clamped to max_w."""
    data_w = max((len(r.get(key) or "") for r in rows), default=0)
    return min(max(data_w, len(header)) + 2, max_w)


def _print_translation_table(data: dict):
    """Print translate response as a formatted table."""
    print()
    rows = data.get("csv", [])
    if not rows:
        print(red("  ✗  No translations found for that term / language combination."))
        print(f"     Check {cyan('languages')} and {cyan('countries')} to see what is loaded.")
        print()
        return

    term      = data.get("term", "")
    src_lang  = data.get("source_lang", "")
    tgt_lang  = data.get("target_lang", "")
    country   = data.get("country")
    country_str = f"  country={country}" if country else ""
    print(dim(f"  {term!r}   {src_lang} → {tgt_lang}{country_str}   ({len(rows)} result{'s' if len(rows) != 1 else ''})"))

    cg = _col_width(rows, "generic_name",        "Generic Name",        28)
    cb = _col_width(rows, "brand_name",           "Brand Name",          22)
    co = _col_width(rows, "original_language",    "Original Language",   20)
    ct = _col_width(rows, "translated_language",  "Translated Language", 20)

    hdr = (f"  {bold('Brand Name'):<{cb+9}}"
           f"{bold('Generic Name'):<{cg+9}}"
           f"{bold('Original Language'):<{co+9}}"
           f"{bold('Translated Language')}")
    print()
    print(hdr)
    print(dim("  " + "─" * (cb + cg + co + ct)))

    for r in rows:
        brand  = r.get("brand_name")  or dim("—")
        gen    = r.get("generic_name") or ""
        orig   = r.get("original_language")   or ""
        trans  = r.get("translated_language") or ""
        print(f"  {brand:<{cb}}{gen:<{cg}}{orig:<{co}}{trans:<{ct}}")
    print()


def _print_csv_table(rows: list):
    """Print the full drug catalogue table."""
    if not rows:
        print(yellow("  No drug entries found. Upload a CSV first:  csv upload <path>"))
        return

    cg = _col_width(rows, "generic_name",       "Generic Name",     24)
    cb = _col_width(rows, "brand_name",          "Brand Name",       20)
    cc = 8
    co = _col_width(rows, "original_language",   "Orig Lang",        16)
    ct = _col_width(rows, "translated_language", "Trans Lang",       16)

    print()
    print(bold(f"  {'Generic Name':<{cg}}{'Brand Name':<{cb}}{'Country':<{cc}}"
               f"{'Orig Lang':<{co}}{'Trans Lang':<{ct}}"))
    print(dim("  " + "─" * (cg + cb + cc + co + ct)))

    for r in rows:
        brand   = r.get("brand_name") or dim("—")
        country = r.get("country")    or "—"
        print(f"  {(r.get('generic_name') or ''):<{cg}}"
              f"{brand:<{cb}}"
              f"{country:<{cc}}"
              f"{(r.get('original_language') or ''):<{co}}"
              f"{(r.get('translated_language') or ''):<{ct}}")
    print()


def _print_countries_table(rows: list):
    if not rows:
        print(yellow("  No countries found. Upload a CSV first:  csv upload <path>"))
        return
    print()
    print(bold(f"  {'ISO':<8}Languages"))
    print(dim("  " + "─" * 40))
    for r in rows:
        iso   = r.get("iso_code") or "—"
        langs = r.get("languages") or []
        print(f"  {iso:<8}{', '.join(langs) if langs else dim('(no translations yet)')}")
    print()


def _print_help():
    print(f"""
  {bold('Commands')}
    {cyan('translate')}            Translate a drug name between languages
    {cyan('audit <term>')}         Quality audit — missing translations / brands
    {cyan('csv upload <path>')}    Upload a Codex CSV to Neo4j
    {cyan('csv list')}             Show all drugs + brands from Neo4j
    {cyan('countries')}            List supported countries and their languages
    {cyan('languages')}            List language codes loaded in Neo4j
    {cyan('health')}               Check API + Neo4j connection
    {cyan('help')}                 Show this message
    {cyan('quit')}                 Exit

  {bold('Translate inputs')}
    Drug name   : generic name (Ibuprofen) or brand name (Advil)
    Source lang : ISO 639-1 code of the input language  (e.g. en, es)
    Target lang : ISO 639-1 code of the desired language (e.g. es, uk)
    Country     : ISO 3166-1 alpha-2 to narrow results (e.g. MX) — optional

  {bold('Swagger UI')}  {dim(API_BASE + '/docs')}
""")


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {label}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return val if val else default


#Command handlers

def cmd_health():
    data = _request("get", "/health")
    if not data:
        return
    neo4j = green("✓ connected") if data["neo4j"] else red("✗ unreachable")
    print(f"\n  API   : {green('✓ running')}  (v{data['api_version']})")
    print(f"  Neo4j : {neo4j}\n")


def cmd_languages():
    data = _request("get", "/languages")
    if not data:
        return
    langs = data.get("languages", [])
    if langs:
        print(f"\n  Loaded: {', '.join(langs)}\n")
    else:
        print(yellow("\n  No languages loaded yet. Upload a CSV:  csv upload <path>\n"))


def cmd_csv_upload(path: str):
    if not path:
        path = _prompt("Path to CSV file")
    if not path:
        print(red("  ✗  No path provided"))
        return
    if not os.path.exists(path):
        print(red(f"  ✗  File not found: {path}"))
        return
    print(f"  Uploading {os.path.basename(path)}…")
    with open(path, "rb") as f:
        data = _request("post", "/csv/upload",
                        files={"file": (os.path.basename(path), f, "text/csv")})
    if data:
        meta = data.get("metadata", {})
        print(green(f"  ✓  {data['message']}"))
        print(dim(f"     Timestamp : {meta.get('generated_at', '—')}"))
        print(dim(f"     Rows      : {meta.get('row_count', '—')}"))
        print()


def cmd_csv_list():
    print("  Fetching drug catalogue…")
    data = _request("get", "/csv")
    if not data:
        return
    meta = data.get("metadata", {})
    rows = data.get("csv", [])
    print(dim(f"  Source: {meta.get('source','—')}  |  "
              f"Rows: {meta.get('row_count', len(rows))}  |  "
              f"Generated: {meta.get('generated_at','—')}"))
    _print_csv_table(rows)


def cmd_countries():
    print("  Fetching countries…")
    data = _request("get", "/countries")
    if not data:
        return
    meta = data.get("metadata", {})
    rows = data.get("csv", [])
    print(dim(f"  Source: {meta.get('source','—')}  |  "
              f"Countries: {meta.get('row_count', len(rows))}  |  "
              f"Generated: {meta.get('generated_at','—')}"))
    _print_countries_table(rows)


def cmd_translate():
    """Prompt for drug name, source language, target language, and country."""
    term        = _prompt("Drug name (generic or brand)")
    source_lang = _prompt("Source language code (e.g. en, es, fr)")
    target_lang = _prompt("Target language code (e.g. es, uk, fr)")
    country     = _prompt("Country code (e.g. US, MX) or Enter to search all")

    if not term or not source_lang or not target_lang:
        print(red("  ✗  Drug name, source language, and target language are required"))
        return

    payload = {"term": term, "source_lang": source_lang, "target_lang": target_lang}
    if country:
        payload["country"] = country.strip().upper()

    data = _request("post", "/translate", json=payload)
    if data:
        _print_translation_table(data)


def cmd_audit(term: str):
    if not term:
        print(red("  ✗  Provide a term:  audit Ibuprofen"))
        return
    data = _request("get", f"/audit/{term}")
    if not data:
        return
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


#Main loop

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
        elif lower == "countries":
            cmd_countries()
        elif lower == "translate":
            cmd_translate()
        elif lower.startswith("csv"):
            parts = raw.split(None, 2)
            sub   = parts[1].lower() if len(parts) > 1 else ""
            if sub == "upload":
                cmd_csv_upload(parts[2] if len(parts) > 2 else "")
            elif sub == "list":
                cmd_csv_list()
            else:
                print(red(f"  ✗  Unknown csv sub-command '{sub}'"))
                print(f"     Use {cyan('csv upload <path>')} or {cyan('csv list')}")
        elif lower.startswith("audit"):
            parts = raw.split(None, 1)
            term  = parts[1] if len(parts) > 1 else _prompt("Term to audit")
            cmd_audit(term.strip())
        else:
            print(yellow(f"  Unknown command '{raw}'.  Type {cyan('help')} for a list."))


if __name__ == "__main__":
    main()
