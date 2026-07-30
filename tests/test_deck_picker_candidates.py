# tests/test_deck_picker_candidates.py
from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints


def test_excludes_banned_and_respects_copies():
    pool = CardPool({"Shock": 4, "Bolt": 1, "Cancel": 4})
    deck = [CardRef("Bolt")]
    constraints = DeckConstraints(banned=frozenset({"Cancel"}), max_copies=4)
    names = [c.name for c in legal_candidates(pool, deck, constraints)]
    assert "Cancel" not in names
    assert "Bolt" not in names  # only 1 available
    assert "Shock" in names


def test_full_deck_yields_empty():
    pool = CardPool({"Shock": 4})
    deck = [CardRef("Shock")] * 60
    assert legal_candidates(pool, deck, DeckConstraints()) == []


def test_basics_always_available():
    pool = CardPool({"Shock": 4})
    names = [c.name for c in legal_candidates(pool, [], DeckConstraints())]
    assert "Island" in names
