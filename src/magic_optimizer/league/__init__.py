# src/magic_optimizer/league/__init__.py
from magic_optimizer.league.elo import expected_score, update_elo
from magic_optimizer.league.job import OptimizationJob
from magic_optimizer.league.stop_policy import (
    EloPlateauStop,
    ManualReviewStop,
    WinrateThresholdStop,
)
from magic_optimizer.league.store import League
from magic_optimizer.league.types import JobState, LeagueDeck

__all__ = [
    "EloPlateauStop",
    "JobState",
    "League",
    "LeagueDeck",
    "ManualReviewStop",
    "OptimizationJob",
    "WinrateThresholdStop",
    "expected_score",
    "update_elo",
]
