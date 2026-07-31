# src/magic_optimizer/deck_picker/complete.py
from __future__ import annotations

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
    DeckStep,
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


def complete_deck_with_trajectory(
    policy: HeuristicNextCardPolicy,
    pool: CardPool,
    constraints: DeckConstraints,
    *,
    seed_deck: list[CardRef] | None = None,
    alt_k: int = 3,
) -> tuple[list[CardRef], list[DeckStep]]:
    """Build a deck and record every pin/seed/add/fill_basics step."""
    deck: list[CardRef] = []
    steps: list[DeckStep] = []

    for name in constraints.pinned:
        card = CardRef(name)
        deck.append(card)
        steps.append(
            DeckStep(action="pin", card=card, score=0.0, alternatives=(), index=len(deck))
        )

    if seed_deck:
        for card in seed_deck:
            deck.append(card)
            steps.append(
                DeckStep(
                    action="seed",
                    card=card,
                    score=0.0,
                    alternatives=(),
                    index=len(deck),
                )
            )

    while count_non_basics(deck) < constraints.non_basic_target:
        picks = policy.next_card(pool, deck, constraints, k=50)
        if not picks:
            break
        non_basic_picks = [s for s in picks if s.card.name not in BASIC_LANDS]
        if not non_basic_picks:
            break
        chosen = non_basic_picks[0]
        alts = tuple(non_basic_picks[1 : 1 + max(0, alt_k)])
        deck.append(chosen.card)
        steps.append(
            DeckStep(
                action="add",
                card=chosen.card,
                score=chosen.score,
                alternatives=alts,
                index=len(deck),
            )
        )

    before_basics = len(deck)
    deck = fill_basics(deck, constraints)
    for card in deck[before_basics:]:
        steps.append(
            DeckStep(
                action="fill_basics",
                card=card,
                score=0.0,
                alternatives=(),
                index=0,  # filled after; set below
            )
        )
    # Fix indices for fill_basics steps
    fixed: list[DeckStep] = []
    size = before_basics
    for step in steps:
        if step.action == "fill_basics":
            size += 1
            fixed.append(
                DeckStep(
                    action=step.action,
                    card=step.card,
                    score=step.score,
                    alternatives=step.alternatives,
                    index=size,
                )
            )
        else:
            fixed.append(step)
    return deck, fixed


def complete_deck(
    policy: HeuristicNextCardPolicy,
    pool: CardPool,
    constraints: DeckConstraints,
    *,
    seed_deck: list[CardRef] | None = None,
) -> list[CardRef]:
    deck, _ = complete_deck_with_trajectory(
        policy, pool, constraints, seed_deck=seed_deck
    )
    return deck
