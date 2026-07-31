# tests/test_league_elo.py
from magic_optimizer.league.elo import expected_score, update_elo


def test_expected_equal_ratings():
    assert abs(expected_score(1000, 1000) - 0.5) < 1e-9


def test_update_elo_winner_gains():
    a2, b2 = update_elo(1000, 1000, 1.0, k=32)
    assert a2 > 1000
    assert b2 < 1000
    assert abs((a2 - 1000) - (1000 - b2)) < 1e-9
