# src/magic_optimizer/deck_picker/pools.py
from __future__ import annotations

from collections import Counter

from magic_optimizer.deck_picker.types import CardPool


def pool_from_card_rows(rows: list[dict]) -> CardPool:
    counts: Counter[str] = Counter()
    for row in rows:
        name = str(row.get("card_name", "")).strip()
        if not name:
            continue
        counts[name] += int(row.get("amount", 0))
    return CardPool(dict(counts))


def union_pools(*pools: CardPool) -> CardPool:
    counts: Counter[str] = Counter()
    for pool in pools:
        counts.update(pool.available)
    return CardPool(dict(counts))
