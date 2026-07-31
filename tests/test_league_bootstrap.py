# tests/test_league_bootstrap.py
import random

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.league.bootstrap import deck_from_policy, seed_league_from_pool
from magic_optimizer.league.store import League


def _pool(n: int = 40) -> CardPool:
    return CardPool({f"Card{i}": 4 for i in range(n)})


def _ratings(n: int = 40) -> dict[str, float]:
    return {f"Card{i}": float(i) for i in range(n)}


def test_deck_from_policy_returns_names():
    pool = _pool()
    constraints = DeckConstraints(deck_size=60, non_basic_target=40)
    policy = HeuristicNextCardPolicy(_ratings())
    names = deck_from_policy(policy, pool, constraints)
    assert len(names) == 60
    assert all(isinstance(n, str) for n in names)


def test_seed_league_adds_n_decks():
    league = League()
    pool = _pool()
    constraints = DeckConstraints(deck_size=60, non_basic_target=40)
    policy = HeuristicNextCardPolicy(_ratings())
    ids = seed_league_from_pool(
        league, policy, pool, constraints, n=3, rng=random.Random(0)
    )
    assert len(ids) == 3
    assert len(league) == 3
    for deck_id in ids:
        d = league.get(deck_id)
        assert len(d.cards) == 60
        assert d.provenance == "bootstrap"
