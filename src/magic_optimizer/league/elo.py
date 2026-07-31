# src/magic_optimizer/league/elo.py
"""Elo rating helpers for the deck league."""

from __future__ import annotations


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def update_elo(
    rating_a: float,
    rating_b: float,
    score_a: float,
    *,
    k: float = 32.0,
) -> tuple[float, float]:
    """Return (new_a, new_b). score_a is 1.0 win / 0.0 loss / 0.5 draw for A."""
    ea = expected_score(rating_a, rating_b)
    eb = expected_score(rating_b, rating_a)
    new_a = rating_a + k * (score_a - ea)
    new_b = rating_b + k * ((1.0 - score_a) - eb)
    return new_a, new_b
