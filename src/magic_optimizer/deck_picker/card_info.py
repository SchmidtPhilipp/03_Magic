"""Lazy Scryfall-backed card_info with on-disk cache (for color limits)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import requests

_DEFAULT_CACHE = Path(__file__).resolve().parents[3] / "runs" / "card_color_cache.json"
_UA = {
    "User-Agent": "MagicOptimizer/1.0 (philipp; card-color-cache)",
    "Accept": "application/json",
}


def make_card_info(
    cache_path: Path | str | None = None,
    *,
    allow_network: bool = True,
    save_every: int = 25,
    request_timeout: float = 8.0,
) -> Callable[[str], dict[str, Any] | None]:
    path = Path(cache_path) if cache_path else _DEFAULT_CACHE
    cache: dict[str, Any] = {}
    if path.exists():
        try:
            cache = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}
    dirty = 0

    def _save() -> None:
        nonlocal dirty
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
        dirty = 0

    def _touch() -> None:
        nonlocal dirty
        dirty += 1
        if dirty >= max(1, save_every):
            _save()

    def card_info(name: str) -> dict[str, Any] | None:
        key = name.strip()
        if not key:
            return None
        hit = cache.get(key)
        if isinstance(hit, dict) and (
            "color_identity" in hit or hit.get("_missing")
        ):
            if hit.get("_missing"):
                return None
            return hit
        if not allow_network:
            return None
        time.sleep(0.08)
        try:
            r = requests.get(
                "https://api.scryfall.com/cards/named",
                params={"exact": key},
                headers=_UA,
                timeout=request_timeout,
            )
            if r.status_code == 404:
                r = requests.get(
                    "https://api.scryfall.com/cards/named",
                    params={"fuzzy": key},
                    headers=_UA,
                    timeout=request_timeout,
                )
            if r.status_code == 404:
                cache[key] = {"_missing": True}
                _touch()
                return None
            if r.status_code == 429:
                # Do not block deckbuild for a full minute — caller fail-closes.
                return None
            if r.status_code != 200:
                return None
            data = r.json()
            face = data["card_faces"][0] if data.get("card_faces") else data
            entry = {
                "name": data.get("name", key),
                "mana_cost": data.get("mana_cost") or face.get("mana_cost") or "",
                "cmc": float(data.get("cmc") or 0),
                "type_line": data.get("type_line") or face.get("type_line") or "",
                "color_identity": list(data.get("color_identity") or []),
                "colors": list(data.get("colors") or face.get("colors") or []),
            }
            cache[key] = entry
            _touch()
            return entry
        except requests.RequestException:
            return None

    card_info.flush = _save  # type: ignore[attr-defined]
    return card_info
