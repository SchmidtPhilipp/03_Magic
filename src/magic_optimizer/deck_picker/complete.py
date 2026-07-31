# src/magic_optimizer/deck_picker/complete.py
from __future__ import annotations

from typing import Callable

from magic_optimizer.deck_picker.heuristic import NextCardPolicy
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
    """Only allocate basics to colors with positive weight (no forced 5-color)."""
    weights = {color: max(0, color_pips.get(color, 0)) for color in _WUBRG_ORDER}
    active = [c for c in _WUBRG_ORDER if weights[c] > 0]
    if not active:
        return _equal_split_counts(lands_needed)

    total = sum(weights[c] for c in active)
    raw = {color: lands_needed * weights[color] / total for color in active}
    counts = {color: int(raw[color]) for color in active}
    assigned = sum(counts.values())
    remainder = lands_needed - assigned

    fractional = sorted(
        active,
        key=lambda color: (raw[color] - counts[color], -_WUBRG_ORDER.index(color)),
        reverse=True,
    )
    for color in fractional[:remainder]:
        counts[color] += 1

    return {
        _COLOR_TO_LAND[color]: counts.get(color, 0) for color in _WUBRG_ORDER if color in counts
    }


def _land_counts(lands_needed: int, color_pips: dict[str, int] | None) -> dict[str, int]:
    if color_pips is None or sum(color_pips.get(c, 0) for c in _WUBRG_ORDER) == 0:
        return _equal_split_counts(lands_needed)
    return _proportional_split_counts(lands_needed, color_pips)


def fill_basics(
    decklist: list[CardRef],
    constraints: DeckConstraints,
    color_pips: dict[str, int] | None = None,
) -> list[CardRef]:
    """Append basics. With color_pips, only colors with weight > 0 get lands."""
    deck = list(decklist)
    lands_needed = constraints.deck_size - len(deck)
    if lands_needed <= 0:
        return deck

    counts = _land_counts(lands_needed, color_pips)
    for land in _WUBRG_LANDS:
        for _ in range(counts.get(land, 0)):
            deck.append(CardRef(land))
    return deck


def refill_basics(
    decklist: list[CardRef],
    constraints: DeckConstraints,
    color_pips: dict[str, int] | None = None,
) -> list[CardRef]:
    """Strip existing basics and refill from color_pips."""
    from magic_optimizer.deck_picker.mana import strip_basics

    return fill_basics(strip_basics(decklist), constraints, color_pips=color_pips)


def complete_deck_with_trajectory(
    policy: NextCardPolicy,
    pool: CardPool,
    constraints: DeckConstraints,
    *,
    seed_deck: list[CardRef] | None = None,
    alt_k: int = 3,
    color_pips: dict[str, int] | None = None,
    card_info: Callable[[str], dict | None] | None = None,
) -> tuple[list[CardRef], list[DeckStep]]:
    """Build a deck and record every pin/seed/add/fill_basics step.

    Prefer color_pips or card_info (Scryfall-like) so basics match the mana base.
    Without either, falls back to equal WUBRG (legacy — usually wrong for real play).
    """
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

    resolved_pips = color_pips
    if resolved_pips is None and card_info is not None:
        from magic_optimizer.deck_picker.mana import estimate_deck_color_pips

        resolved_pips = estimate_deck_color_pips(deck, card_info=card_info)

    before_basics = len(deck)
    deck = fill_basics(deck, constraints, color_pips=resolved_pips)
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
    policy: NextCardPolicy,
    pool: CardPool,
    constraints: DeckConstraints,
    *,
    seed_deck: list[CardRef] | None = None,
    color_pips: dict[str, int] | None = None,
    card_info: Callable[[str], dict | None] | None = None,
) -> list[CardRef]:
    deck, _ = complete_deck_with_trajectory(
        policy,
        pool,
        constraints,
        seed_deck=seed_deck,
        color_pips=color_pips,
        card_info=card_info,
    )
    return deck
