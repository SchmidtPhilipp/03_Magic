# tests/test_deck_picker_types.py
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
    ScoredCard,
)


def test_card_ref_normalizes_and_hashes():
    a = CardRef(" Lightning Bolt ")
    b = CardRef("Lightning Bolt")
    assert a.name == "Lightning Bolt"
    assert a == b
    assert hash(a) == hash(b)


def test_card_pool_basics_unlimited():
    pool = CardPool({"Shock": 2})
    assert pool.copies_available("Shock") == 2
    assert pool.copies_available("Island") >= 10**6
    assert "Island" in BASIC_LANDS


def test_deck_constraints_defaults():
    c = DeckConstraints()
    assert c.deck_size == 60
    assert c.max_copies == 4
    assert c.non_basic_target == 40
    assert c.banned == frozenset()
    assert c.pinned == ()
