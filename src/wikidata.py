"""Fetch creators' death years from Wikidata (CC0).

For each creator name we search Wikidata, keep candidates that are humans
(P31 = Q5) with a date of death (P570), and pick the candidate whose death
year matches the editor's expected year if there is one; otherwise the top
human result. Mismatches are recorded so a person can check them.
Results are cached in data/wikidata_creators.json so the analysis is
reproducible offline.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": "public-domain-geography/1.0 (research; Amir Khan, Independent Researcher)"}
CACHE = Path(__file__).resolve().parents[1] / "data" / "wikidata_creators.json"


def _get(params: dict) -> dict:
    for attempt in range(5):
        r = requests.get(API, params={**params, "format": "json"}, headers=UA, timeout=30)
        if r.status_code == 200:
            return r.json()
        time.sleep(2 * (attempt + 1))
    r.raise_for_status()
    return {}


def _death_year(entity: dict) -> int | None:
    claims = entity.get("claims", {}).get("P570", [])
    years = []
    for c in claims:
        try:
            t = c["mainsnak"]["datavalue"]["value"]["time"]  # e.g. +1950-01-21T00:00:00Z
            years.append(int(t[1:5]))
        except (KeyError, TypeError, ValueError):
            continue
    return min(years) if years else None


def _is_human(entity: dict) -> bool:
    for c in entity.get("claims", {}).get("P31", []):
        try:
            if c["mainsnak"]["datavalue"]["value"]["id"] == "Q5":
                return True
        except (KeyError, TypeError):
            continue
    return False


def resolve(name: str, expected: int | None) -> dict:
    hits = _get({"action": "wbsearchentities", "search": name, "language": "en", "type": "item", "limit": 7})
    ids = [h["id"] for h in hits.get("search", [])]
    if not ids:
        return {"name": name, "qid": None, "death_year": None, "label": None, "match": "not_found"}
    ents = _get({"action": "wbgetentities", "ids": "|".join(ids), "props": "claims|labels", "languages": "en"})
    cands = []
    for qid in ids:
        e = ents.get("entities", {}).get(qid, {})
        if not _is_human(e):
            continue
        dy = _death_year(e)
        if dy is None:
            continue
        cands.append((qid, dy, e.get("labels", {}).get("en", {}).get("value")))
    if not cands:
        return {"name": name, "qid": None, "death_year": None, "label": None, "match": "no_human_with_death"}
    chosen = next((c for c in cands if expected is not None and c[1] == expected), cands[0])
    match = "ok" if expected is None or chosen[1] == expected else "MISMATCH"
    return {"name": name, "qid": chosen[0], "death_year": chosen[1], "label": chosen[2], "match": match,
            "expected": expected}


def fetch_all(pairs: list[tuple[str, int | None]], refresh: bool = False) -> dict:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() and not refresh else {}
    for name, expected in pairs:
        if name in cache and not refresh:
            continue
        cache[name] = resolve(name, expected)
        time.sleep(0.3)
    CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))
    return cache
