# tests/test_league_stop_policy.py
from magic_optimizer.league.stop_policy import (
    EloPlateauStop,
    ManualReviewStop,
    WinrateThresholdStop,
)
from magic_optimizer.league.types import JobState


def test_winrate_threshold():
    stop = WinrateThresholdStop(threshold=0.55, min_games=20)
    assert not stop.should_stop(JobState(best_winrate=0.9, games_vs_top=10))
    assert not stop.should_stop(JobState(best_winrate=0.5, games_vs_top=30))
    assert stop.should_stop(JobState(best_winrate=0.55, games_vs_top=20))


def test_elo_plateau():
    stop = EloPlateauStop(epsilon=5.0, window=3)
    assert not stop.should_stop(JobState(elo_history=[1000, 1020, 1040, 1060]))
    assert stop.should_stop(JobState(elo_history=[1000, 1002, 1003, 1004, 1005]))


def test_manual_review():
    stop = ManualReviewStop()
    assert not stop.should_stop(JobState())
    assert stop.should_stop(JobState(cancelled=True))
