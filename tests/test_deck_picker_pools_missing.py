from magic_optimizer.deck_picker.missing import missing_cards
from magic_optimizer.deck_picker.pools import pool_from_card_rows, union_pools
from magic_optimizer.deck_picker.types import CardPool, CardRef


def test_pool_from_rows_and_union():
    a = pool_from_card_rows(
        [{"card_name": "Shock", "amount": 2}, {"card_name": "Shock", "amount": 1}]
    )
    assert a.copies_available("Shock") == 3
    b = CardPool({"Bolt": 2, "Shock": 1})
    u = union_pools(a, b)
    assert u.copies_available("Shock") == 4
    assert u.copies_available("Bolt") == 2


def test_missing_cards_ignores_basics():
    owned = CardPool({"Shock": 1})
    deck = [CardRef("Shock"), CardRef("Shock"), CardRef("Island"), CardRef("Bolt")]
    miss = missing_cards(deck, owned)
    assert miss == [("Bolt", 1), ("Shock", 1)]
