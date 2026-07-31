"""Lightweight Scryfall lookup for scan review."""

from __future__ import annotations

import time
from typing import Any

import requests

_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_CACHE_TTL = 3600
_HEADERS = {
    "User-Agent": "MagicOptimizer/1.0 (philipp; collection-scan)",
    "Accept": "application/json",
}


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
            headers=_HEADERS,
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
            "image_uri": _small_image_uri(data),
        }
        _CACHE[key] = (now, result)
        return result
    except requests.RequestException:
        return None


def _small_image_uri(data: dict[str, Any]) -> str | None:
    uris = data.get("image_uris") or {}
    if uris.get("small"):
        return str(uris["small"])
    faces = data.get("card_faces") or []
    if faces:
        face_uris = faces[0].get("image_uris") or {}
        if face_uris.get("small"):
            return str(face_uris["small"])
    return None


def scryfall_get(url: str, *, params: dict | None = None, timeout: float = 15):
    """GET with Scryfall-required User-Agent."""
    return requests.get(url, params=params, headers=_HEADERS, timeout=timeout)


def attach_image_uri(det: dict[str, Any]) -> dict[str, Any]:
    """Ensure detection dict has image_uri / collector_number when possible."""
    out = dict(det)
    if out.get("image_uri") and out.get("collector_number"):
        return out
    name = (out.get("detected_name") or "").strip()
    if not name or name.lower() == "unbekannt":
        return out
    meta = lookup_card_name(name)
    if not meta:
        return out
    if not out.get("image_uri"):
        out["image_uri"] = meta.get("image_uri")
    if not out.get("collector_number"):
        out["collector_number"] = meta.get("collector_number")
    if not out.get("scryfall_id"):
        out["scryfall_id"] = meta.get("scryfall_id")
    if not out.get("set_code"):
        out["set_code"] = meta.get("set_code")
    return out


def enrich_detections_payload(
    detections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [attach_image_uri(d) for d in detections]
