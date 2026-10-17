# tests/test_deck_picker_synergy_bonus.py
from __future__ import annotations

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints
from magic_optimizer.synergy.graph import SynergyGraph


def test_synergy_changes_next_card_order():
    pool = CardPool({"A": 4, "B": 4, "C": 4})
    constraints = DeckConstraints(deck_size=60, non_basic_target=40, max_copies=4)
    ratings = {"A": 1.0, "B": 1.0, "C": 1.05}
    g = SynergyGraph()
    g.add_deck(["A", "B"], weight=10.0)

    plain = HeuristicNextCardPolicy(ratings)
    boosted = HeuristicNextCardPolicy(ratings, synergy=g, synergy_scale=1.0)

    deck = [CardRef("A")]
    plain_top = plain.next_card(pool, deck, constraints, k=3)[0].card.name
    boost_top = boosted.next_card(pool, deck, constraints, k=3)[0].card.name
    # Without synergy C is slightly higher; with synergy B should win
    assert plain_top == "C"
    assert boost_top == "B"
