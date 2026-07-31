# tests/test_league_job.py
from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.league.job import OptimizationJob
from magic_optimizer.league.stop_policy import WinrateThresholdStop
from magic_optimizer.league.store import League
from magic_optimizer.league.types import LeagueDeck
from magic_optimizer.match_oracle.stub import StubMatchOracle


def _cards(name: str) -> list[str]:
    return [name] * 60


def test_challenge_requires_opponent():
    league = League()
    job = OptimizationJob(league, StubMatchOracle(seed=1), WinrateThresholdStop())
    try:
        job.challenge(_cards("A"), deck_id="a")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_challenge_updates_elo():
    league = League()
    league.add(LeagueDeck(id="boot", cards=_cards("Boot"), elo=1000))
    job = OptimizationJob(
        league,
        StubMatchOracle(seed=2),
        WinrateThresholdStop(threshold=0.99, min_games=1000),
        games_per_match=7,
        seed=0,
    )
    summary = job.challenge(_cards("Challenger"), deck_id="c1")
    assert "winner_id" in summary
    assert league.get("c1").games == 7 or league.get("boot").games == 7
    assert summary["should_stop"] is False


def test_run_until_stop_respects_threshold():
    league = League()
    league.add(LeagueDeck(id="boot", cards=_cards("Boot")))
    # Very easy stop: threshold 0, min_games 0 after first challenge with any result
    job = OptimizationJob(
        league,
        StubMatchOracle(seed=3),
        WinrateThresholdStop(threshold=0.0, min_games=0),
        games_per_match=3,
        seed=1,
    )
    n = 0

    def build() -> list[str]:
        nonlocal n
        n += 1
        return _cards(f"D{n}")

    state = job.run_until_stop(build, max_challenges=10)
    assert state.challenges >= 1
    assert state.challenges <= 10
