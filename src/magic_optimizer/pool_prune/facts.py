# src/magic_optimizer/pool_prune/facts.py
from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


LookupFn = Callable[[str], dict[str, Any] | None]

_TYPE_BUCKETS: tuple[str, ...] = (
    "creature",
    "instant",
    "sorcery",
    "artifact",
    "enchantment",
    "planeswalker",
    "land",
    "battle",
)


def parse_stat(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "*":
        return None
    # Handle "1+*" style as non-comparable
    if any(ch in text for ch in "*+"):
        try:
            return float(text.replace("*", "").replace("+", "") or "nan")
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def type_bucket(type_line: str) -> str:
    lower = (type_line or "").lower()
    # Card faces use "//"; take front for bucket
    front = lower.split("//", 1)[0]
    for bucket in _TYPE_BUCKETS:
        if bucket in front:
            return bucket
    return "other"


@dataclass(frozen=True)
class CardFacts:
    name: str
    cmc: float
    type_line: str
    colors: frozenset[str]
    power: float | None
    toughness: float | None
    keywords: frozenset[str]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["colors"] = sorted(self.colors)
        d["keywords"] = sorted(self.keywords)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardFacts:
        return cls(
            name=str(data["name"]),
            cmc=float(data.get("cmc") or 0.0),
            type_line=str(data.get("type_line") or ""),
            colors=frozenset(str(c) for c in (data.get("colors") or [])),
            power=parse_stat(data.get("power")),
            toughness=parse_stat(data.get("toughness")),
            keywords=frozenset(str(k) for k in (data.get("keywords") or [])),
        )


def facts_from_scryfall_dict(data: dict[str, Any]) -> CardFacts:
    """Build CardFacts from a Scryfall-like card dict."""
    colors = data.get("color_identity") or data.get("colors") or []
    # Double-faced: prefer face[0] for P/T when missing on root
    power = data.get("power")
    toughness = data.get("toughness")
    type_line = data.get("type_line") or ""
    if (power is None or toughness is None) and data.get("card_faces"):
        face0 = data["card_faces"][0] or {}
        power = power if power is not None else face0.get("power")
        toughness = toughness if toughness is not None else face0.get("toughness")
        if not type_line:
            type_line = face0.get("type_line") or ""
    keywords = data.get("keywords") or []
    return CardFacts(
        name=str(data.get("name") or ""),
        cmc=float(data.get("cmc") or 0.0),
        type_line=str(type_line),
        colors=frozenset(str(c) for c in colors),
        power=parse_stat(power),
        toughness=parse_stat(toughness),
        keywords=frozenset(str(k) for k in keywords),
    )


def _default_lookup(name: str) -> dict[str, Any] | None:
    """Fetch full Scryfall card JSON by fuzzy name."""
    from magic_optimizer.vision.scryfall import scryfall_get

    try:
        resp = scryfall_get(
            "https://api.scryfall.com/cards/named",
            params={"fuzzy": name},
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


class CardFactsStore:
    def __init__(
        self,
        *,
        cache_path: str | Path | None = None,
        lookup: LookupFn | None = None,
    ) -> None:
        self.cache_path = Path(cache_path) if cache_path else None
        self.lookup = lookup or _default_lookup
        self._mem: dict[str, CardFacts] = {}
        if self.cache_path and self.cache_path.is_file():
            self._load_disk()

    def _load_disk(self) -> None:
        assert self.cache_path is not None
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        for name, payload in raw.items():
            if isinstance(payload, dict):
                self._mem[str(name)] = CardFacts.from_dict(payload)

    def _save_disk(self) -> None:
        if self.cache_path is None:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {name: facts.to_dict() for name, facts in self._mem.items()}
        self.cache_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )

    def get(self, name: str) -> CardFacts | None:
        if name in self._mem:
            return self._mem[name]
        data = self.lookup(name)
        if not data:
            return None
        # Ensure name key matches request for pool keys
        if not data.get("name"):
            data = {**data, "name": name}
        facts = facts_from_scryfall_dict(data)
        # Store under the pool name the caller asked for
        facts = CardFacts(
            name=name,
            cmc=facts.cmc,
            type_line=facts.type_line,
            colors=facts.colors,
            power=facts.power,
            toughness=facts.toughness,
            keywords=facts.keywords,
        )
        self._mem[name] = facts
        self._save_disk()
        return facts

    def get_many(self, names: Iterable[str]) -> dict[str, CardFacts]:
        out: dict[str, CardFacts] = {}
        for name in names:
            facts = self.get(str(name))
            if facts is not None:
                out[str(name)] = facts
        return out
