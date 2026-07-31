# tests/test_deck_picker_trajectory_modify.py
from magic_optimizer.deck_picker.complete import complete_deck_with_trajectory
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.modify import propose_swaps
from magic_optimizer.deck_picker.types import BASIC_LANDS, CardPool, CardRef, DeckConstraints


def test_complete_deck_with_trajectory_records_each_add():
    pool = CardPool({f"Card{i}": 4 for i in range(50)})
    ratings = {f"Card{i}": float(i) for i in range(50)}
    policy = HeuristicNextCardPolicy(ratings)
    constraints = DeckConstraints(pinned=("Card49",), non_basic_target=5)
    deck, steps = complete_deck_with_trajectory(policy, pool, constraints)
    assert len(deck) == 60
    assert steps[0].action == "pin"
    assert steps[0].card.name == "Card49"
    adds = [s for s in steps if s.action == "add"]
    assert len(adds) == 4  # target 5 including pin
    assert all(s.card.name not in BASIC_LANDS for s in adds)
    assert any(s.action == "fill_basics" for s in steps)


def test_propose_swaps_suggests_upgrade():
    pool = CardPool({"Weak": 4, "Strong": 4, "Other": 4})
    ratings = {"Weak": 1.0, "Strong": 9.0, "Other": 5.0}
    policy = HeuristicNextCardPolicy(ratings)
    # Full skeleton of weaks + basics would be heavy; use small non_basic and then
    # a partial-style deck: one Weak that can be swapped for Strong.
    deck = [CardRef("Weak")] + [CardRef("Island")] * 59
    swaps = propose_swaps(
        policy,
        pool,
        deck,
        DeckConstraints(deck_size=60, non_basic_target=40),
        k=3,
    )
    assert swaps
    assert swaps[0].remove.name == "Weak"
    assert swaps[0].add.name == "Strong"
    assert swaps[0].score_delta > 0
