#!/usr/bin/env python3
"""
Codex CLI — terminal interface for the Codex Translation API.
Every command makes one HTTP request. Start the API first via launcher.py.
"""

import sys
import os
import argparse

try:
    import httpx
except ImportError:
    print("Missing dependency: pip install httpx")
    sys.exit(1)

API_BASE = os.getenv("CODEX_API_URL", "http://localhost:8000")
TIMEOUT  = 15

BOLD  = "\033[1m"
GREEN = "\033[32m"
YELLOW= "\033[33m"
RED   = "\033[31m"
CYAN  = "\033[36m"
DIM   = "\033[2m"
RESET = "\033[0m"

def bold(s):   return f"{BOLD}{s}{RESET}"
def green(s):  return f"{GREEN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"


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
        print(f"     Start the app first:  {cyan('python launcher.py')}\n")
        return None
    except httpx.TimeoutException:
        print(red("  ✗  Request timed out"))
        return None


def _col_width(rows, key, header, max_w):
    data_w = max((len(str(r.get(key) or "")) for r in rows), default=0)
    return min(max(data_w, len(header)) + 2, max_w)


def _print_terms_table(rows: list):
    if not rows:
        print(yellow("  No entries found."))
        return

    csi = _col_width(rows, "source_id",   "Source ID",   16)
    csn = _col_width(rows, "source_name", "Source",      16)
    cn  = _col_width(rows, "name",        "Name",        28)
    ct  = _col_width(rows, "type",        "Type",        26)
    cco = _col_width(rows, "country",     "Country",      9)
    cl  = _col_width(rows, "language",    "Language",    14)
    csim = _col_width(rows, "similarity", "Score", 8)

    print()
    print(bold(
        f"  {'Source ID':<{csi}}{'Source':<{csn}}"
        f"{'Name':<{cn}}{'Type':<{ct}}{'Country':<{cco}}{'Language':<{cl}}{'Score':<{csim}}"
    ))
    print(dim("  " + "─" * (csi + csn + cn + ct + cco + cl)))

    for r in rows:
        print(
            f"  {str(r.get('source_id')    or dim('—')):<{csi}}"
            f"{str(r.get('source_name')  or dim('—')):<{csn}}"
            f"{str(r.get('name')         or ''):<{cn}}"
            f"{str(r.get('type')         or ''):<{ct}}"
            f"{str(r.get('country')      or dim('—')):<{cco}}"
            f"{str(r.get('language')     or dim('—')):<{cl}}"
            f"{str(round(r.get('similarity', 1.0), 3) if r.get('similarity') else ''):<{csim}}"
        )
    print()


def _print_translate_table(data: dict):
    print()
    results = data.get("results", [])
    if not results:
        print(red("  ✗  No translations found."))
        print(f"     Check {cyan('languages')} and {cyan('countries')} to see what is loaded.")
        print()
        return

    term    = data.get("term", "")
    src     = data.get("source_lang", "")
    tgt     = data.get("target_lang", "")
    country = data.get("target_country") or ""
    src_flt = data.get("source_name") or ""
    filters = "  ".join(filter(None, [
        f"country={country}" if country else "",
        f"source={src_flt}" if src_flt else "",
    ]))
    print(dim(f"  {term!r}  {src} → {tgt}  {filters}  ({len(results)} result{'s' if len(results) != 1 else ''})"))
    _print_terms_table(results)


def _print_help():
    print(f"""
  {bold('Commands')}
    {cyan('translate')}                 Translate a drug name between languages
    {cyan('csv list')}                  Show all terms in the database
    {cyan('csv concept <id>')}          Show all terms for a Concept ID
    {cyan('csv country <code>')}        Show all terms for a country (e.g. US)
    {cyan('csv language <lang>')}       Show all terms for a language (e.g. English or en)
    {cyan('csv upload <path>')}         Upload a Codex CSV
    {cyan('sources')}                   List all data sources
    {cyan('source <name>')}             Show all terms from a specific source
    {cyan('countries')}                 List countries and their languages
    {cyan('languages')}                 List languages loaded in the database
    {cyan('reset')}                     Wipe all data (with confirmation)
    {cyan('health')}                    Check API + Neo4j connection
    {cyan('help')}                      Show this message
    {cyan('quit')}                      Exit

  {bold('CSV format')}
    Concept ID, Source ID, Source Name, Name, Type, Country, Language
    Concept ID is optional — auto-generated if blank.
    Type values: Generic/Active Ingredient  or  Brand

  {bold('Swagger UI')}  {dim(API_BASE + '/docs')}
""")


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {label}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return val if val else default


def cmd_health():
    data = _request("get", "/health")
    if not data:
        return
    neo4j = green("✓ connected") if data["neo4j"] else red("✗ unreachable")
    print(f"\n  API   : {green('✓ running')}  (v{data['api_version']})")
    print(f"  Neo4j : {neo4j}\n")


def cmd_translate():
    term           = _prompt("Drug name")
    source_lang    = _prompt("Source language (e.g. en, English)")
    target_lang    = _prompt("Target language (e.g. es, Spanish)")
    target_country = _prompt("Target country code (e.g. MX) or Enter for all")
    source_name    = _prompt("Filter by source name (e.g. RxNorm) or Enter for all")

    if not term or not source_lang or not target_lang:
        print(red("  ✗  Drug name, source language, and target language are required"))
        return

    payload = {
        "term":        term,
        "source_lang": source_lang,
        "target_lang": target_lang,
    }
    if target_country:
        payload["target_country"] = target_country.strip().upper()
    if source_name:
        payload["source_name"] = source_name.strip()

    data = _request("post", "/translate", json=payload)
    if data:
        _print_translate_table(data)


def cmd_csv_list():
    data = _request("get", "/csv")
    if not data:
        return
    rows = data.get("rows", [])
    print(dim(f"  {data.get('row_count', len(rows))} terms  |  {data.get('generated_at', '')}"))
    _print_terms_table(rows)


def cmd_csv_concept(concept_id: str):
    if not concept_id:
        concept_id = _prompt("Concept ID")
    if not concept_id:
        print(red("  ✗  No Concept ID provided"))
        return
    data = _request("get", f"/csv/concept/{concept_id}")
    if data:
        rows = data.get("rows", [])
        print(dim(f"  Concept: {concept_id}  |  {data.get('row_count', len(rows))} terms"))
        _print_terms_table(rows)


def cmd_csv_country(country: str):
    if not country:
        country = _prompt("Country code (e.g. US)")
    if not country:
        print(red("  ✗  No country provided"))
        return
    data = _request("get", f"/csv/country/{country.upper()}")
    if data:
        rows = data.get("rows", [])
        print(dim(f"  Country: {country.upper()}  |  {data.get('row_count', len(rows))} terms"))
        _print_terms_table(rows)


def cmd_csv_language(language: str):
    if not language:
        language = _prompt("Language (e.g. English or en)")
    if not language:
        print(red("  ✗  No language provided"))
        return
    data = _request("get", f"/csv/language/{language}")
    if data:
        rows = data.get("rows", [])
        print(dim(f"  Language: {language}  |  {data.get('row_count', len(rows))} terms"))
        _print_terms_table(rows)


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
        print(green(f"  ✓  {data['message']}"))
        print(dim(f"     Timestamp : {data.get('generated_at', '—')}"))
        print(dim(f"     Rows      : {data.get('row_count', '—')}"))
        print()


def cmd_sources():
    data = _request("get", "/sources")
    if not data:
        return
    sources = data.get("sources", [])
    if not sources:
        print(yellow("\n  No sources found. Upload a CSV with a Source Name column.\n"))
        return
    cn = _col_width(sources, "source_name", "Source", 28)
    print()
    print(bold(f"  {'Source':<{cn}}{'Terms':>8}  Last Uploaded"))
    print(dim("  " + "─" * (cn + 40)))
    for s in sources:
        print(f"  {str(s.get('source_name') or ''):<{cn}}"
              f"{str(s.get('term_count', 0)):>8}  "
              f"{s.get('last_uploaded') or dim('—')}")
    print()


def cmd_source_detail(source_name: str):
    if not source_name:
        source_name = _prompt("Source name")
    if not source_name:
        print(red("  ✗  No source name provided"))
        return
    data = _request("get", f"/sources/{source_name}")
    if data:
        rows = data.get("rows", [])
        print(dim(f"  Source: {source_name}  |  {data.get('row_count', len(rows))} terms"))
        _print_terms_table(rows)


def cmd_countries():
    data = _request("get", "/countries")
    if not data:
        return
    countries = data.get("countries", [])
    if not countries:
        print(yellow("  No countries found. Upload a CSV first.\n"))
        return
    print()
    print(bold(f"  {'Country':<10}Languages"))
    print(dim("  " + "─" * 50))
    for r in countries:
        langs = ", ".join(r.get("languages") or []) or dim("—")
        print(f"  {r.get('country', ''):<10}{langs}")
    print()


def cmd_languages():
    data = _request("get", "/languages")
    if not data:
        return
    langs = data.get("languages", [])
    if langs:
        print(f"\n  Loaded: {', '.join(langs)}\n")
    else:
        print(yellow("\n  No languages loaded yet.\n"))


def cmd_reset():
    print()
    print(red("  ⚠  WARNING: This will permanently delete all data."))
    confirm = _prompt("Type RESET to confirm, or Enter to cancel")
    if confirm != "RESET":
        print(yellow("  Cancelled — no data was deleted"))
        print()
        return
    data = _request("post", "/reset")
    if data:
        print(green(f"  ✓  {data['message']}"))
    print()

def upload_sample_data(folder: str = "sample_data"):
    if not os.path.isdir(folder):
        print(red(f"  ✗  Sample data folder not found: {folder}"))
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith(".csv")]

    if not files:
        print(yellow(f"  No CSV files found in {folder}"))
        return

    print(bold(f"\nUploading sample data from '{folder}'...\n"))

    for fname in files:
        path = os.path.join(folder, fname)
        print(f"  Uploading {fname}...")

        with open(path, "rb") as f:
            data = _request(
                "post",
                "/csv/upload",
                files={"file": (fname, f, "text/csv")}
            )

        if data:
            print(green(f"    ✓ {data['message']}"))
        else:
            print(red(f"    ✗ Failed to upload {fname}"))

    print(green("\n  ✓ Sample data upload complete\n"))

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
        parts = raw.split(None, 2)

        if lower in ("quit", "exit", "q"):
            print("Bye.")
            break
        elif lower in ("help", "?"):
            _print_help()
        elif lower == "health":
            cmd_health()
        elif lower == "translate":
            cmd_translate()
        elif lower == "sources":
            cmd_sources()
        elif lower.startswith("source "):
            cmd_source_detail(parts[1] if len(parts) > 1 else "")
        elif lower == "countries":
            cmd_countries()
        elif lower == "languages":
            cmd_languages()
        elif lower == "reset":
            cmd_reset()
        elif lower.startswith("csv"):
            sub = parts[1].lower() if len(parts) > 1 else ""
            arg = parts[2].strip() if len(parts) > 2 else ""
            if sub == "list":
                cmd_csv_list()
            elif sub == "concept":
                cmd_csv_concept(arg)
            elif sub == "country":
                cmd_csv_country(arg)
            elif sub == "language":
                cmd_csv_language(arg)
            elif sub == "upload":
                cmd_csv_upload(arg)
            else:
                print(red(f"  ✗  Unknown csv sub-command '{sub}'"))
                print(f"     Use {cyan('help')} to see available commands.")
        else:
            print(yellow(f"  Unknown command '{raw}'.  Type {cyan('help')} for a list."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-data", nargs="?", const="sample_data",
                        help="Upload all CSVs from a folder")
    args = parser.parse_args()
    if args.sample_data:
        upload_sample_data(args.sample_data)

    main()
