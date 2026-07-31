# tests/test_league_progress.py
from magic_optimizer.league.progress import snapshot_progress
from magic_optimizer.league.store import League
from magic_optimizer.league.types import JobState, LeagueDeck


def test_snapshot_progress():
    league = League()
    league.add(LeagueDeck(id="a", cards=["X"] * 60))
    prog = snapshot_progress(
        JobState(challenges=3, best_deck_id="a", best_winrate=0.7, games_vs_top=10),
        league,
    )
    assert prog.challenges == 3
    assert prog.league_size == 1
    assert prog.best_deck_id == "a"
    d = prog.to_dict()
    assert "forge_available" in d
