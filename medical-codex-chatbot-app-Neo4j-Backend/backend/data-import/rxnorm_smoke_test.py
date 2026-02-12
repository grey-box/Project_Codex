#!/usr/bin/env python3
"""
rxnorm_smoke_test.py

A minimal “can we talk to RxNorm?” script.

For each demo drug name:
- Look up an RxCUI (normalized search)
- Fetch concept properties (name, TTY)
- Fetch related concepts (ingredients, clinical & branded drugs, brand names)
- Fetch a few NDCs
- Print a compact summary

No API key required.
"""

from __future__ import annotations
import requests
from typing import Any, Dict, List, Optional

BASE = "https://rxnav.nlm.nih.gov/REST"

# Try a few varied strings (ingredient, brand, generic)
DEMO_DRUGS = [
    "acetaminophen",
    "atorvastatin",
    "metformin",
    "amoxicillin",
    "lipitor",        # brand
    "ibuprofen 200 mg tablet",  # phrase-y test
]

def _get(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def find_rxcui_by_string(name: str, search: int = 1) -> Optional[str]:
    """
    Use RxNorm 'findRxcuiByString' with normalized search (search=1).
    Returns the first RxCUI if found.
    """
    url = f"{BASE}/rxcui.json"
    j = _get(url, {"name": name, "search": search})
    ids = (j or {}).get("idGroup", {}).get("rxnormId") or []
    return ids[0] if ids else None

def get_properties(rxcui: str) -> Dict[str, Any]:
    """getRxConceptProperties -> concept name, tty, etc."""
    url = f"{BASE}/rxcui/{rxcui}/properties.json"
    j = _get(url)
    return (j or {}).get("properties") or {}

def get_all_related(rxcui: str, expand: str = "psn") -> Dict[str, Any]:
    """
    getAllRelatedInfo -> returns groups by TTY (e.g., IN, BN, SCD, SBD, SCDF, DF, etc.)
    """
    url = f"{BASE}/rxcui/{rxcui}/allrelated.json"
    return _get(url, {"expand": expand}).get("allRelatedGroup") or {}

def get_ndcs(rxcui: str, limit: int = 10) -> List[str]:
    """getNDCs -> list of active NDCs (CMS 11-digit derivative)."""
    url = f"{BASE}/rxcui/{rxcui}/ndcs.json"
    ndc_list = _get(url).get("ndcGroup", {}).get("ndcList", {}).get("ndc") or []
    return ndc_list[:limit]

def _grp(all_related: Dict[str, Any], tty: str) -> List[Dict[str, Any]]:
    """Pull one related concept group by TTY and return conceptProperties[] (or empty)."""
    groups = all_related.get("conceptGroup") or []
    for g in groups:
        if g.get("tty") == tty:
            props = g.get("conceptProperties") or []
            return props if isinstance(props, list) else [props]
    return []

def summarize_one(name: str) -> None:
    print(f"\n=== {name} ===")
    rxcui = find_rxcui_by_string(name, search=1)
    if not rxcui:
        print("No RxCUI found")
        return

    props = get_properties(rxcui)
    pretty_name = props.get("name") or "(no name)"
    tty = props.get("tty") or "(no tty)"
    print(f"RxCUI: {rxcui} | {pretty_name} | TTY: {tty}")

    rel = get_all_related(rxcui, expand="psn")
    # Common groups to preview:
    ing = _grp(rel, "IN")     # ingredient
    scd = _grp(rel, "SCD")    # clinical drug
    sbd = _grp(rel, "SBD")    # branded drug
    bn  = _grp(rel, "BN")     # brand name

    def sample_names(items: List[Dict[str, Any]], k=5) -> str:
        names = [x.get("name") for x in items if x.get("name")]
        return ", ".join(names[:k]) + (f" (+{max(0, len(names)-k)} more)" if len(names) > k else "")

    if ing:
        print(f"Ingredients (IN): {sample_names(ing)}")
    if scd:
        print(f"Clinical drugs (SCD): {sample_names(scd)}")
    if sbd:
        print(f"Branded drugs (SBD): {sample_names(sbd)}")
    if bn:
        print(f"Brand names (BN): {sample_names(bn)}")

    ndcs = get_ndcs(rxcui, limit=8)
    if ndcs:
        print(f"NDCs (first {len(ndcs)}): {', '.join(ndcs)}")

def main():
    for n in DEMO_DRUGS:
        try:
            summarize_one(n)
        except requests.HTTPError as e:
            print(f"HTTP error for '{n}': {e}")
        except Exception as e:
            print(f"Error for '{n}': {e}")

if __name__ == "__main__":
    main()

