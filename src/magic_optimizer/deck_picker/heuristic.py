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
    def __init__(
        self,
        ratings: dict[str, float] | None = None,
        *,
        synergy=None,
        synergy_scale: float = 0.1,
    ) -> None:
        self._ratings = ratings or {}
        self._synergy = synergy
        self._synergy_scale = float(synergy_scale)

    def next_card(
        self,
        collection: CardPool,
        decklist: list[CardRef],
        constraints: DeckConstraints,
        *,
        k: int = 10,
    ) -> list[ScoredCard]:
        from magic_optimizer.synergy.graph import bonus_for_candidate

        scored: list[ScoredCard] = []
        for c in legal_candidates(collection, decklist, constraints):
            score = float(self._ratings.get(c.name, 0.0))
            if self._synergy is not None:
                score += bonus_for_candidate(
                    self._synergy,
                    decklist,
                    c.name,
                    scale=self._synergy_scale,
                )
            scored.append(ScoredCard(card=c, score=score))
        scored.sort(key=lambda s: (-s.score, s.card.name))
        return scored[: max(0, k)]
