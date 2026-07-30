# src/magic_optimizer/deck_picker/missing.py
from __future__ import annotations

from collections import Counter

from magic_optimizer.deck_picker.types import BASIC_LANDS, CardPool, CardRef


def missing_cards(deck: list[CardRef], owned: CardPool) -> list[tuple[str, int]]:
    counts = Counter(c.name for c in deck)
    missing: list[tuple[str, int]] = []
    for name in sorted(counts):
        if name in BASIC_LANDS:
            continue
        needed = counts[name] - owned.copies_available(name)
        if needed > 0:
            missing.append((name, needed))
    return missing
