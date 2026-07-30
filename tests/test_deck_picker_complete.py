# tests/test_deck_picker_complete.py
from magic_optimizer.deck_picker.complete import complete_deck, fill_basics
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
)


def test_fill_basics_reaches_sixty_deterministically():
    deck = [CardRef("Shock")] * 40
    out = fill_basics(deck, DeckConstraints())
    assert len(out) == 60
    assert sum(1 for c in out if c.name in BASIC_LANDS) == 20
    assert fill_basics(deck, DeckConstraints()) == out


def test_complete_deck_includes_pins_and_size():
    pool = CardPool({f"Card{i}": 4 for i in range(50)})
    ratings = {f"Card{i}": float(i) for i in range(50)}
    constraints = DeckConstraints(
        pinned=("Card49",),
        non_basic_target=40,
        banned=frozenset(),
    )
    policy = HeuristicNextCardPolicy(ratings)
    deck = complete_deck(policy, pool, constraints)
    assert len(deck) == 60
    assert deck[0].name == "Card49" or any(c.name == "Card49" for c in deck)
    assert sum(1 for c in deck if c.name not in BASIC_LANDS) == 40
