# src/magic_optimizer/deck_picker/candidates.py
from __future__ import annotations

from collections import Counter

from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
)


def legal_candidates(
    pool: CardPool,
    decklist: list[CardRef],
    constraints: DeckConstraints,
) -> list[CardRef]:
    if len(decklist) >= constraints.deck_size:
        return []

    counts = Counter(c.name for c in decklist)
    banned = {b.strip() for b in constraints.banned}

    names: set[str] = set(pool.available.keys()) | set(BASIC_LANDS)
    result: list[CardRef] = []
    for name in sorted(names):
        if name in banned:
            continue
        limit = min(constraints.max_copies, pool.copies_available(name))
        if counts[name] >= limit:
            continue
        if limit <= 0:
            continue
        result.append(CardRef(name))
    return result
