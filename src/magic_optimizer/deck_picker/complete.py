# src/magic_optimizer/deck_picker/complete.py
from __future__ import annotations

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
)

_WUBRG_ORDER: tuple[str, ...] = ("W", "U", "B", "R", "G")
_WUBRG_LANDS: tuple[str, ...] = ("Plains", "Island", "Swamp", "Mountain", "Forest")
_COLOR_TO_LAND: dict[str, str] = dict(zip(_WUBRG_ORDER, _WUBRG_LANDS, strict=True))


def count_non_basics(decklist: list[CardRef]) -> int:
    return sum(1 for card in decklist if card.name not in BASIC_LANDS)


def _equal_split_counts(lands_needed: int) -> dict[str, int]:
    base, remainder = divmod(lands_needed, len(_WUBRG_LANDS))
    counts = {land: base for land in _WUBRG_LANDS}
    for land in _WUBRG_LANDS[:remainder]:
        counts[land] += 1
    return counts


def _proportional_split_counts(
    lands_needed: int, color_pips: dict[str, int]
) -> dict[str, int]:
    weights = {color: max(0, color_pips.get(color, 0)) for color in _WUBRG_ORDER}
    total = sum(weights.values())
    if total <= 0:
        return _equal_split_counts(lands_needed)

    raw = {color: lands_needed * weights[color] / total for color in _WUBRG_ORDER}
    counts = {color: int(raw[color]) for color in _WUBRG_ORDER}
    assigned = sum(counts.values())
    remainder = lands_needed - assigned

    fractional = sorted(
        _WUBRG_ORDER,
        key=lambda color: (raw[color] - counts[color], -_WUBRG_ORDER.index(color)),
        reverse=True,
    )
    for color in fractional[:remainder]:
        counts[color] += 1

    return {_COLOR_TO_LAND[color]: counts[color] for color in _WUBRG_ORDER}


def _land_counts(lands_needed: int, color_pips: dict[str, int] | None) -> dict[str, int]:
    if color_pips is None or sum(color_pips.get(c, 0) for c in _WUBRG_ORDER) == 0:
        return _equal_split_counts(lands_needed)
    return _proportional_split_counts(lands_needed, color_pips)


def fill_basics(
    decklist: list[CardRef],
    constraints: DeckConstraints,
    color_pips: dict[str, int] | None = None,
) -> list[CardRef]:
    deck = list(decklist)
    lands_needed = constraints.deck_size - len(deck)
    if lands_needed <= 0:
        return deck

    counts = _land_counts(lands_needed, color_pips)
    for land in _WUBRG_LANDS:
        for _ in range(counts[land]):
            deck.append(CardRef(land))
    return deck


def complete_deck(
    policy: HeuristicNextCardPolicy,
    pool: CardPool,
    constraints: DeckConstraints,
    *,
    seed_deck: list[CardRef] | None = None,
) -> list[CardRef]:
    deck: list[CardRef] = [CardRef(name) for name in constraints.pinned]
    if seed_deck:
        deck.extend(seed_deck)

    while count_non_basics(deck) < constraints.non_basic_target:
        picks = policy.next_card(pool, deck, constraints, k=50)
        if not picks:
            break
        pick = next(
            (scored.card for scored in picks if scored.card.name not in BASIC_LANDS),
            None,
        )
        if pick is None:
            break
        deck.append(pick)

    return fill_basics(deck, constraints)
