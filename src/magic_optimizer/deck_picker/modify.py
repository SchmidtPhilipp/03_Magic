# src/magic_optimizer/deck_picker/modify.py
"""Suggest modifications to an existing decklist."""

from __future__ import annotations

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
    SwapProposal,
)


def propose_swaps(
    policy: HeuristicNextCardPolicy,
    pool: CardPool,
    decklist: list[CardRef],
    constraints: DeckConstraints,
    *,
    k: int = 5,
    max_removals: int = 20,
) -> list[SwapProposal]:
    """
    For each removable non-basic in the deck (lowest rating first), ask
    next_card what would replace it. Return upgrades sorted by score_delta desc.
    """
    ratings = getattr(policy, "_ratings", {}) or {}
    non_basics = [c for c in decklist if c.name not in BASIC_LANDS]
    # Unique positions: evaluate each distinct name once (worst copy)
    by_name: dict[str, CardRef] = {}
    for card in non_basics:
        by_name[card.name] = card
    removable = sorted(
        by_name.values(),
        key=lambda c: (float(ratings.get(c.name, 0.0)), c.name),
    )[: max(0, max_removals)]

    proposals: list[SwapProposal] = []
    for remove in removable:
        # Drop one copy of remove
        removed = False
        trial: list[CardRef] = []
        for card in decklist:
            if not removed and card.name == remove.name:
                removed = True
                continue
            trial.append(card)
        if not removed:
            continue

        remove_score = float(ratings.get(remove.name, 0.0))
        picks = policy.next_card(pool, trial, constraints, k=max(1, k))
        for scored in picks:
            if scored.card.name == remove.name:
                continue
            if scored.card.name in BASIC_LANDS:
                continue
            delta = scored.score - remove_score
            if delta <= 0:
                continue
            proposals.append(
                SwapProposal(
                    remove=remove,
                    add=scored.card,
                    score_delta=delta,
                    remove_score=remove_score,
                    add_score=scored.score,
                )
            )
            break  # best replacement for this removal

    proposals.sort(key=lambda p: (-p.score_delta, p.remove.name, p.add.name))
    return proposals[: max(0, k)]


def apply_swap(decklist: list[CardRef], proposal: SwapProposal) -> list[CardRef]:
    """Return a new decklist with one copy of remove replaced by add."""
    out: list[CardRef] = []
    replaced = False
    for card in decklist:
        if not replaced and card.name == proposal.remove.name:
            out.append(proposal.add)
            replaced = True
        else:
            out.append(card)
    if not replaced:
        raise ValueError(f"card not in deck: {proposal.remove.name}")
    return out
