"""Stochastic sealed / mixed-draft pool generation for opponent metas."""
from __future__ import annotations

import csv
import json
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests
import yaml

from magic_optimizer.deck_picker.types import BASIC_LANDS, CardPool

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HISTORY = ROOT / "data/meta/playgroup_product_history.yaml"
DEFAULT_CACHE = ROOT / "runs/scryfall_set_cards_cache.json"
UA = {
    "User-Agent": "MagicOptimizer/1.0 (philipp; sealed-pool-sim)",
    "Accept": "application/json",
}


def load_confirmed_sets(history_path: Path | None = None) -> list[str]:
    path = history_path or DEFAULT_HISTORY
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [str(s["code"]).upper() for s in data.get("confirmed_sets", [])]


def union_nonbasic_copies(union_csv: Path) -> int:
    n = 0
    with union_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("card_name") or "").strip()
            if name in BASIC_LANDS:
                continue
            n += max(1, int(float(row.get("amount") or 1)))
    return n


def load_union_pool(union_csv: Path) -> CardPool:
    counts: Counter[str] = Counter()
    with union_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("card_name") or "").strip()
            if not name or name in BASIC_LANDS:
                continue
            counts[name] += max(1, int(float(row.get("amount") or 1)))
    return CardPool(dict(counts))


def _load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache_path: Path, cache: dict) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def fetch_set_cards(
    set_code: str,
    *,
    cache: dict | None = None,
    cache_path: Path | None = None,
) -> dict[str, list[str]]:
    cache_path = cache_path or DEFAULT_CACHE
    cache = cache if cache is not None else _load_cache(cache_path)
    key = set_code.upper()
    if key in cache and cache[key].get("common"):
        return cache[key]

    buckets: dict[str, list[str]] = {
        "common": [],
        "uncommon": [],
        "rare": [],
        "mythic": [],
    }
    url: str | None = "https://api.scryfall.com/cards/search"
    params: dict[str, str] | None = {
        "q": f"e:{key} unique:prints -is:digital -is:token",
        "unique": "prints",
    }
    while url:
        r = requests.get(url, params=params, headers=UA, timeout=60)
        params = None
        if r.status_code != 200:
            raise RuntimeError(
                f"Scryfall error {r.status_code} for set {key}: {r.text[:200]}"
            )
        payload = r.json()
        for card in payload.get("data", []):
            rarity = (card.get("rarity") or "").lower()
            name = card.get("name") or ""
            if not name or rarity not in buckets:
                continue
            if name.split("//")[0].strip() in BASIC_LANDS:
                continue
            if name not in buckets[rarity]:
                buckets[rarity].append(name)
        url = payload.get("next_page")
        time.sleep(0.12)

    cache[key] = buckets
    _save_cache(cache_path, cache)
    return buckets


def open_draft_booster(
    buckets: dict[str, list[str]], rng: random.Random
) -> list[str]:
    cards: list[str] = []
    commons = buckets.get("common") or []
    uncommons = buckets.get("uncommon") or []
    rares = buckets.get("rare") or []
    mythics = buckets.get("mythic") or []

    def pick(pool: list[str], n: int) -> list[str]:
        if not pool:
            return []
        if len(pool) >= n:
            return rng.sample(pool, n)
        return [rng.choice(pool) for _ in range(n)]

    cards.extend(pick(commons, 10))
    cards.extend(pick(uncommons, 3))
    if mythics and rng.random() < 0.125:
        cards.append(rng.choice(mythics))
    elif rares:
        cards.append(rng.choice(rares))
    elif mythics:
        cards.append(rng.choice(mythics))
    return cards


def generate_sealed_pool(
    *,
    target_copies: int,
    seed: int,
    sets: list[str] | None = None,
    players: int = 5,
    packs_per_player: int = 6,
    promo_rate: float = 0.25,
    history_path: Path | None = None,
    cache_path: Path | None = None,
) -> dict[str, Any]:
    """Open sealed/mixed-draft events until pool reaches target_copies."""
    rng = random.Random(seed)
    set_list = sets or load_confirmed_sets(history_path)
    cache_path = cache_path or DEFAULT_CACHE
    cache = _load_cache(cache_path)
    buckets_by_set = {
        s: fetch_set_cards(s, cache=cache, cache_path=cache_path) for s in set_list
    }

    pool: Counter[str] = Counter()
    set_from: Counter[str] = Counter()
    events = 0
    packs_opened = 0
    promos = 0

    promo_pool: list[str] = []
    for s in set_list:
        promo_pool.extend(buckets_by_set[s].get("mythic") or [])
        promo_pool.extend(buckets_by_set[s].get("rare") or [])

    while sum(pool.values()) < target_copies:
        events += 1
        if rng.random() < 0.15 and len(set_list) >= 2:
            a, b = rng.sample(set_list, 2)
            pack_plan = [a] * 3 + [b] * 3
            event_kind = f"mixed_draft:{a}+{b}"
        else:
            s = rng.choice(set_list)
            pack_plan = [s] * packs_per_player
            event_kind = f"sealed:{s}"

        stopped = False
        for _player in range(players):
            for set_code in pack_plan:
                for name in open_draft_booster(buckets_by_set[set_code], rng):
                    pool[name] += 1
                    set_from[set_code] += 1
                packs_opened += 1
                if sum(pool.values()) >= target_copies:
                    stopped = True
                    break
            if stopped:
                break
            if promo_pool and rng.random() < promo_rate:
                name = rng.choice(promo_pool)
                pool[name] += 1
                promos += 1
                set_from["PROMO"] += 1
            if sum(pool.values()) >= target_copies:
                stopped = True
                break
        if stopped:
            break

    return {
        "seed": seed,
        "target_copies": target_copies,
        "events": events,
        "packs_opened": packs_opened,
        "promos_injected": promos,
        "event_kind_last": event_kind,
        "unique_cards": len(pool),
        "total_copies": sum(pool.values()),
        "copies_by_set_opened": dict(set_from),
        "confirmed_sets": set_list,
        "pool": dict(pool),
    }


def sealed_pool_as_card_pool(**kwargs: Any) -> CardPool:
    result = generate_sealed_pool(**kwargs)
    return CardPool(dict(result["pool"]))


def default_ratings_for_pool(pool: CardPool) -> dict[str, float]:
    """Deterministic placeholder ratings when Scryfall ratings are absent."""
    out: dict[str, float] = {}
    for name in pool.available:
        out[name] = 50.0 + (sum(ord(c) for c in name) % 40)
    return out
