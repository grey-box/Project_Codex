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
import pytest
import platform
import subprocess

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
  {bold('Translation Commands')}
    {cyan('<drug name>')}            Translate a term (prompts for language + country)
    {cyan('audit <term>')}           Quality audit — missing translations / brands
    {cyan('demo')}                   Load built-in sample data
    {cyan('load <path>')}            Upload a language pack JSON
    {cyan('languages')}              List languages loaded in Neo4j

  {bold('User Management Commands')}
    {cyan('user add')}               Create a new user
    {cyan('users')}                  List all users (or filter by role)
    {cyan('user get <email>')}       Get details for a specific user
    {cyan('user update <email>')}    Update user fields (name, role, affiliation, pwd)
    {cyan('user delete <email>')}    Delete a user node
    {cyan('role get <email>')}       Get a specific user's role
    {cyan('role set <email>')}       Update a specific user's role

  {bold('System Commands')}
    {cyan('clear')}                  Clear the terminal screen
    {cyan('health')}                 Check API + Neo4j connection
    {cyan('help')}                   Show this message
    {cyan('quit')}                   Exit

  {bold('Swagger UI')}  {dim(API_BASE + '/docs')}
""")
    
def _print_user(data: dict):
    print()
    print(bold(f"  Email       : {data.get('email')}"))
    print(f"  Real Name   : {data.get('real_name')}")
    print(f"  Role        : {cyan(data.get('role', ''))}")
    print(f"  Affiliation : {data.get('affiliation')}")
    if data.get("created_at"):
        print(f"  Created At  : {dim(str(data.get('created_at')))}")
    print()


def _print_users_list(users: list):
    print()
    if not users:
        print(yellow("  No users found."))
        print()
        return
    print(bold(f"  Found {len(users)} user(s):"))
    for u in users:
        print(f"    • {bold(u['email'])}  —  {u['real_name']}  [{cyan(u['role'])}]  ({dim(u['affiliation'])})")
    print()


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
        
def cmd_user_add():
    print(bold("\n  Create New User"))
    email       = _prompt("Email")
    real_name   = _prompt("Real Name")
    password    = _prompt("Password")
    role        = _prompt("Role", default="User")
    affiliation = _prompt("Affiliation", default="General")

    if not email or not real_name or not password:
        print(red("  ✗  Email, Real Name, and Password are required."))
        return

    payload = {
        "email": email,
        "real_name": real_name,
        "password": password,
        "role": role,
        "affiliation": affiliation
    }
    data = _request("post", "/users", json=payload)
    if data:
        print(green("  ✓ User created successfully!"))
        _print_user(data)


def cmd_users_list(role: str = ""):
    path = f"/users?role={role}" if role else "/users"
    data = _request("get", path)
    if data is not None:
        _print_users_list(data)


def cmd_user_get(email: str):
    if not email:
        email = _prompt("User Email")
    if not email:
        print(red("  ✗  Email is required."))
        return
    data = _request("get", f"/users/{email}")
    if data:
        _print_user(data)


def cmd_user_update(email: str):
    if not email:
        email = _prompt("User Email")
    if not email:
        print(red("  ✗  Email is required."))
        return

    print(dim("  Leave fields blank to keep current values."))
    real_name   = _prompt("New Real Name")
    role        = _prompt("New Role")
    affiliation = _prompt("New Affiliation")
    password    = _prompt("New Password")

    payload = {}
    if real_name:   payload["real_name"] = real_name
    if role:        payload["role"] = role
    if affiliation: payload["affiliation"] = affiliation
    if password:    payload["password"] = password

    if not payload:
        print(yellow("  No updates provided."))
        return

    data = _request("patch", f"/users/{email}", json=payload)
    if data:
        print(green("  ✓ User updated successfully!"))
        _print_user(data)


def cmd_user_delete(email: str):
    if not email:
        email = _prompt("User Email to delete")
    if not email:
        print(red("  ✗  Email is required."))
        return

    confirm = _prompt(f"Are you sure you want to delete {email}? (y/N)", default="n")
    if confirm.lower() != "y":
        print("  Cancelled.")
        return

    data = _request("delete", f"/users/{email}")
    if data:
        print(green(f"  ✓  {data['message']}\n"))


def cmd_role_get(email: str):
    if not email:
        email = _prompt("User Email")
    if not email:
        print(red("  ✗  Email is required."))
        return
    data = _request("get", f"/users/{email}/role")
    if data:
        print(f"\n  User : {data['email']}")
        print(f"  Role : {cyan(data['role'])}\n")


def cmd_role_set(email: str):
    if not email:
        email = _prompt("User Email")
    if not email:
        print(red("  ✗  Email is required."))
        return

    new_role = _prompt("New Role")
    if not new_role:
        print(red("  ✗  New role is required."))
        return

    data = _request("put", f"/users/{email}/role", json={"role": new_role})
    if data:
        print(green("  ✓ Role updated successfully!"))
        _print_user(data)
        
def cmd_clear():
    if platform.system() == "Windows":
        subprocess.run("cls", shell=True)
    else:
        subprocess.run(["clear"])


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print(bold("\nCodex Medical Translation — CLI"))
    print(f"  API  : {cyan(API_BASE)}")
    print(f"  Docs : {cyan(API_BASE + '/docs')}")
    print(f"  Type {cyan('health')} to verify connection, {cyan('help')} for all commands.\n")
    
    payload = {
            "email": "some@email.com",
            "real_name": "firstname lastname",
            "password": "hello world",
            "role": "Admin",
            "affiliation": "grey-box"
    }
    data = _request("post", "/users", json=payload)

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
        # elif lower == "tests":
        #     run_tests()
        elif lower == "health":
            cmd_health()
        elif lower == "languages":
            cmd_languages()
        elif lower == "demo":
            cmd_demo()
        elif lower in ("clear", "cls"):
            cmd_clear()
        elif lower.startswith("load"):
            parts = raw.split(None, 1)
            path = parts[1] if len(parts) > 1 else _prompt("Path to language pack JSON")
            cmd_load(path)
        elif lower.startswith("audit"):
            parts = raw.split(None, 1)
            term = parts[1] if len(parts) > 1 else _prompt("Term to audit")
            cmd_audit(term.strip())
        elif lower in ("user add", "user create"):
            cmd_user_add()
        elif lower.startswith("users"):
            parts = raw.split(None, 1)
            role_filter = parts[1] if len(parts) > 1 else ""
            cmd_users_list(role_filter.strip())
        elif lower.startswith("user get"):
            parts = raw.split(None, 2)
            email = parts[2] if len(parts) > 2 else ""
            cmd_user_get(email.strip())
        elif lower.startswith("user update"):
            parts = raw.split(None, 2)
            email = parts[2] if len(parts) > 2 else ""
            cmd_user_update(email.strip())
        elif lower.startswith("user delete"):
            parts = raw.split(None, 2)
            email = parts[2] if len(parts) > 2 else ""
            cmd_user_delete(email.strip())
        elif lower.startswith("role get"):
            parts = raw.split(None, 2)
            email = parts[2] if len(parts) > 2 else ""
            cmd_role_get(email.strip())
        elif lower.startswith("role set"):
            parts = raw.split(None, 2)
            email = parts[2] if len(parts) > 2 else ""
            cmd_role_set(email.strip())
        else:
            cmd_translate(raw)


if __name__ == "__main__":
    main()
