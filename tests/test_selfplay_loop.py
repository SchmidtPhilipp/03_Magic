# tests/test_selfplay_loop.py
from pathlib import Path

from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.league.stop_policy import WinrateThresholdStop
from magic_optimizer.selfplay.loop import SelfPlayLoop
from magic_optimizer.selfplay.oracle_factory import make_oracle


def _pool(n: int = 40) -> CardPool:
    return CardPool({f"Card{i}": 4 for i in range(n)})


def _ratings(n: int = 40) -> dict[str, float]:
    return {f"Card{i}": float(i) for i in range(n)}


def test_selfplay_loop_runs_and_retrains(tmp_path: Path):
    records = tmp_path / "matches.jsonl"
    loop = SelfPlayLoop(
        oracle=make_oracle(backend="stub", seed=0),
        stop_policy=WinrateThresholdStop(threshold=0.0, min_games=0),
        pool=_pool(),
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        ratings=_ratings(),
        records_path=records,
        games_per_match=3,
        seed=1,
        retrain_every=1,
        dim=24,
    )
    result = loop.run(bootstrap_n=2, max_challenges=3)
    assert result["job_state"]["challenges"] >= 1
    assert result["league_size"] >= 2
    assert result["model_trained"] is True
    assert records.exists()
    assert records.read_text(encoding="utf-8").strip()
    assert len(result["standings"]) >= 2
