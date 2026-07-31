# src/magic_optimizer/dreamer/policy.py
from __future__ import annotations

from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import (
    CardPool,
    CardRef,
    DeckConstraints,
    ScoredCard,
)
from magic_optimizer.dreamer.world_model import WorldModel


class DreamerNextCardPolicy:
    def __init__(
        self,
        world_model: WorldModel,
        opponents: list[list[str]],
        *,
        fallback_ratings: dict[str, float] | None = None,
    ) -> None:
        self.world_model = world_model
        self.opponents = [list(o) for o in opponents]
        self._fallback = HeuristicNextCardPolicy(fallback_ratings or {})

    def next_card(
        self,
        collection: CardPool,
        decklist: list[CardRef],
        constraints: DeckConstraints,
        *,
        k: int = 10,
    ) -> list[ScoredCard]:
        if not self.opponents:
            return self._fallback.next_card(
                collection, decklist, constraints, k=k
            )

        scored: list[ScoredCard] = []
        for card in legal_candidates(collection, decklist, constraints):
            trial = [c.name for c in decklist] + [card.name]
            scores = [
                self.world_model.predict_winrate(trial, opp)
                for opp in self.opponents
            ]
            score = float(sum(scores) / len(scores))
            scored.append(ScoredCard(card=card, score=score))
        scored.sort(key=lambda s: (-s.score, s.card.name))
        return scored[: max(0, k)]
