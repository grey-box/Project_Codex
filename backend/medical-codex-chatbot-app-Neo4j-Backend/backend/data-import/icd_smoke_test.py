#!/usr/bin/env python3
# Prints all first layer names under Chapter 21
# Then takes the first one and traverses it fully
# For each node in that subtree, prints a readable summary and the raw JSON

import os
import sys
import json
import requests
from collections import deque
from dotenv import load_dotenv, find_dotenv

# load .env from repo root
env_path = find_dotenv(usecwd=True)
if not env_path:
    print("ERROR: .env not found at repo root")
    sys.exit(1)
load_dotenv(env_path)

ICD_CLIENT_ID = os.getenv("ICD_CLIENT_ID")
ICD_CLIENT_SECRET = os.getenv("ICD_CLIENT_SECRET")
if not ICD_CLIENT_ID or not ICD_CLIENT_SECRET:
    print("ERROR: Missing ICD_CLIENT_ID or ICD_CLIENT_SECRET in .env")
    sys.exit(1)

API_VERSION = "v2"
ACCEPT_LANGUAGE = "en"
ICD_RELEASE_ID = os.getenv("ICD_RELEASE_ID", "2024-01")

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
ICD_BASE = "https://id.who.int/icd"
MMS_BASE = f"{ICD_BASE}/release/11/{ICD_RELEASE_ID}"
MMS_ROOT = f"{MMS_BASE}/mms"

def get_token():
    r = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": "icdapi_access"},
        auth=(ICD_CLIENT_ID, ICD_CLIENT_SECRET),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]

def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "API-Version": API_VERSION,
        "Accept-Language": ACCEPT_LANGUAGE,
    }

def get_json(url, token, params=None):
    r = requests.get(url, headers=headers(token), params=params or {}, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("Request failed", url)
        print("Status", r.status_code)
        print("Body", r.text[:800])
        raise
    return r.json()

def extract_title(node):
    t = node.get("title")
    if isinstance(t, dict):
        return t.get("@value", "")
    if isinstance(t, str):
        return t
    return ""

def extract_code(node):
    return node.get("code") or node.get("theCode") or ""

def extract_def(node):
    d = node.get("definition") or node.get("briefDefinition")
    if isinstance(d, dict):
        return d.get("@value", "")
    if isinstance(d, str):
        return d
    return ""

def ensure_node_min(token, item):
    if isinstance(item, str):
        node_id = item
        node = get_json(node_id, token, params={"properties": "code,title"})
        return node_id, extract_code(node), extract_title(node), node
    if isinstance(item, dict):
        node_id = item.get("@id")
        code = extract_code(item)
        title = extract_title(item)
        if not node_id or not (code or title):
            node = get_json(node_id, token, params={"properties": "code,title"})
            return node_id, extract_code(node), extract_title(node), node
        return node_id, code, title, item
    return None, "", "", {}

def get_children_array(node_json):
    arr = node_json.get("child")
    if isinstance(arr, list) and arr:
        return arr
    arr = node_json.get("descendant")
    if isinstance(arr, list) and arr:
        return arr
    return []

def find_chapter_21(token):
    root = get_json(MMS_ROOT, token, params={"flat": "true"})
    for child in root.get("child", []):
        node_id, code, title, _ = ensure_node_min(token, child)
        if not node_id:
            continue
        if code == "21" or ("Symptoms, signs" in (title or "")):
            return node_id
    return None

def fetch_node_full(token, node_id):
    # no properties filter here so you can see everything the API returns
    return get_json(node_id, token)

def print_summary(node, depth):
    indent = "  " * depth
    code = extract_code(node) or "—"
    title = extract_title(node)
    definition = extract_def(node)
    print(f"{indent}[{code}] {title}")
    if definition:
        d = definition.strip().replace("\n", " ")
        print(f"{indent}  def: {d}")

    # try some common fields if present
    for key in ["synonym", "indexTerm", "inclusion", "exclusion"]:
        val = node.get(key)
        if not val:
            continue
        # values may be arrays of dicts with @value or plain strings
        items = []
        if isinstance(val, list):
            for v in val:
                if isinstance(v, dict):
                    items.append(v.get("@value") or json.dumps(v, ensure_ascii=False))
                else:
                    items.append(str(v))
        elif isinstance(val, dict):
            items.append(val.get("@value") or json.dumps(val, ensure_ascii=False))
        else:
            items.append(str(val))
        if items:
            # cap to keep output readable
            shown = items[:5]
            suffix = "" if len(items) <= 5 else f" (+{len(items)-5} more)"
            print(f"{indent}  {key}: {', '.join(shown)}{suffix}")

def bfs_children_ids(token, node_id):
    # get direct children ids of a node
    subtree = get_json(
        node_id, token,
        params={"include": "descendant", "depth": "1", "properties": "code,title"}
    )
    out = []
    for child in get_children_array(subtree):
        cid, _, _, _ = ensure_node_min(token, child)
        if cid:
            out.append(cid)
    return out

def deep_traverse_and_print(token, start_id):
    # BFS through the selected subtree and print full info per node
    q = deque([(start_id, 0)])
    visited = set()
    while q:
        node_id, depth = q.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        node = fetch_node_full(token, node_id)
        print_summary(node, depth)
        # full JSON payload next for this node
        pretty = json.dumps(node, indent=2, ensure_ascii=False, sort_keys=True)
        indent = "  " * depth
        print(f"{indent}  json:")
        # indent each line of the json block for readability
        for line in pretty.splitlines():
            print(f"{indent}    {line}")
        print()

        for cid in bfs_children_ids(token, node_id):
            if cid not in visited:
                q.append((cid, depth + 1))

def main():
    token = get_token()

    # chapter 21
    ch21_id = find_chapter_21(token)
    if not ch21_id:
        print("Could not locate Chapter 21")
        sys.exit(2)

    # first layer names
    layer1 = get_json(
        ch21_id, token,
        params={"include": "descendant", "depth": "1", "properties": "code,title"}
    )
    children = get_children_array(layer1)

    print("First layer under Chapter 21")
    print("------------------------------------------------------------")
    for i, child in enumerate(children, start=1):
        _, code, title, _ = ensure_node_min(token, child)
        print(f"{i:02d}. {title}  {f'[{code}]' if code else ''}")
    print("------------------------------------------------------------\n")

    if not children:
        print("No first layer items found")
        return

    # pick the first one and go deep
    first_id, _, first_title, _ = ensure_node_min(token, children[0])
    print(f"Deep dive on first item: {first_title or first_id}\n")
    deep_traverse_and_print(token, first_id)

if __name__ == "__main__":
    from collections import deque
    main()

