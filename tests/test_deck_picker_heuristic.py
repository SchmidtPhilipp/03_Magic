# tests/test_deck_picker_heuristic.py
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints


def test_ranks_by_rating_and_respects_k():
    pool = CardPool({"A": 4, "B": 4, "C": 4})
    policy = HeuristicNextCardPolicy({"A": 1.0, "B": 3.0, "C": 2.0})
    top = policy.next_card(pool, [], DeckConstraints(), k=2)
    assert [s.card.name for s in top] == ["B", "C"]
    assert top[0].score == 3.0


def test_skips_banned():
    pool = CardPool({"A": 4, "B": 4})
    policy = HeuristicNextCardPolicy({"A": 9.0, "B": 1.0})
    top = policy.next_card(
        pool, [], DeckConstraints(banned=frozenset({"A"})), k=5
    )
    assert all(s.card.name != "A" for s in top)
    assert top[0].card.name == "B"
