# src/magic_optimizer/deck_picker/trade.py
from __future__ import annotations

from collections import Counter

from magic_optimizer.deck_picker.missing import missing_cards
from magic_optimizer.deck_picker.types import BASIC_LANDS, CardPool, CardRef


def _as_refs(deck: list[CardRef] | list[str]) -> list[CardRef]:
    out: list[CardRef] = []
    for item in deck:
        if isinstance(item, CardRef):
            out.append(item)
        else:
            out.append(CardRef(str(item)))
    return out


def trade_report(
    deck: list[CardRef] | list[str],
    owned: CardPool,
) -> dict:
    """Compare a deck to an owned pool for trade planning."""
    refs = _as_refs(deck)
    missing = missing_cards(refs, owned)
    counts = Counter(c.name for c in refs)
    present: list[tuple[str, int]] = []
    for name in sorted(counts):
        if name in BASIC_LANDS:
            continue
        covered = min(counts[name], owned.copies_available(name))
        if covered > 0:
            present.append((name, covered))
    return {
        "missing": [[name, qty] for name, qty in missing],
        "present": [[name, qty] for name, qty in present],
        "missing_total": int(sum(qty for _, qty in missing)),
        "unique_missing": int(len(missing)),
    }
