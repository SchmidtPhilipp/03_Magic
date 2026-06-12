"""Lightweight Scryfall lookup for scan review."""

from __future__ import annotations

import time
from typing import Any

import requests

_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_CACHE_TTL = 3600


def lookup_card_name(name: str) -> dict[str, Any] | None:
    """Fuzzy search Scryfall; returns first exact-ish match metadata."""
    key = name.strip().lower()
    if not key or key == "unbekannt":
        return None

    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    try:
        resp = requests.get(
            "https://api.scryfall.com/cards/named",
            params={"fuzzy": name},
            timeout=8,
        )
        if resp.status_code != 200:
            _CACHE[key] = (now, None)
            return None
        data = resp.json()
        result = {
            "scryfall_id": data.get("id"),
            "card_name": data.get("name"),
            "set_code": (data.get("set") or "").upper() or None,
            "collector_number": str(data.get("collector_number") or "") or None,
        }
        _CACHE[key] = (now, result)
        return result
    except requests.RequestException:
        return None
