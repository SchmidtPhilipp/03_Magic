# src/magic_optimizer/dreamer/imagine.py
from __future__ import annotations

from magic_optimizer.dreamer.world_model import WorldModel


def score_deck_vs_opponents(
    model: WorldModel,
    deck: list[str],
    opponents: list[list[str]],
) -> float:
    if not opponents:
        return 0.5
    scores = [model.predict_winrate(deck, list(opp)) for opp in opponents]
    return float(sum(scores) / len(scores))


def rank_decks(
    model: WorldModel,
    decks: list[list[str]],
    opponents: list[list[str]],
) -> list[tuple[float, list[str]]]:
    ranked = [
        (score_deck_vs_opponents(model, deck, opponents), list(deck))
        for deck in decks
    ]
    ranked.sort(key=lambda item: (-item[0], item[1][:1]))
    return ranked
