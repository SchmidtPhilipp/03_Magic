# src/magic_optimizer/deck_picker/heuristic.py
from __future__ import annotations

from typing import Protocol

from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.types import (
    CardPool,
    CardRef,
    DeckConstraints,
    ScoredCard,
)


class NextCardPolicy(Protocol):
    def next_card(
        self,
        collection: CardPool,
        decklist: list[CardRef],
        constraints: DeckConstraints,
        *,
        k: int = 10,
    ) -> list[ScoredCard]:
        ...


class HeuristicNextCardPolicy:
    def __init__(self, ratings: dict[str, float] | None = None) -> None:
        self._ratings = ratings or {}

    def next_card(
        self,
        collection: CardPool,
        decklist: list[CardRef],
        constraints: DeckConstraints,
        *,
        k: int = 10,
    ) -> list[ScoredCard]:
        scored = [
            ScoredCard(card=c, score=float(self._ratings.get(c.name, 0.0)))
            for c in legal_candidates(collection, decklist, constraints)
        ]
        scored.sort(key=lambda s: (-s.score, s.card.name))
        return scored[: max(0, k)]
