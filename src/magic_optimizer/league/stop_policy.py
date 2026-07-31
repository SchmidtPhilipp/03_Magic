# src/magic_optimizer/league/stop_policy.py
from __future__ import annotations

from typing import Protocol

from magic_optimizer.league.types import JobState


class StopPolicy(Protocol):
    def should_stop(self, state: JobState) -> bool: ...


class WinrateThresholdStop:
    def __init__(self, *, threshold: float = 0.55, min_games: int = 20) -> None:
        self.threshold = threshold
        self.min_games = min_games

    def should_stop(self, state: JobState) -> bool:
        return (
            state.games_vs_top >= self.min_games
            and state.best_winrate >= self.threshold
        )


class EloPlateauStop:
    def __init__(self, *, epsilon: float = 5.0, window: int = 5) -> None:
        self.epsilon = epsilon
        self.window = window

    def should_stop(self, state: JobState) -> bool:
        hist = state.elo_history
        if len(hist) < self.window + 1:
            return False
        recent = hist[-(self.window + 1) :]
        deltas = [abs(recent[i + 1] - recent[i]) for i in range(len(recent) - 1)]
        return all(d < self.epsilon for d in deltas)


class ManualReviewStop:
    def should_stop(self, state: JobState) -> bool:
        return bool(state.cancelled)
