# tests/test_deck_picker_mana.py
from magic_optimizer.deck_picker.complete import fill_basics
from magic_optimizer.deck_picker.mana import (
    estimate_deck_color_pips,
    pips_from_mana_cost,
    strip_basics,
)
from magic_optimizer.deck_picker.types import CardRef, DeckConstraints


def test_pips_from_mana_cost():
    assert pips_from_mana_cost("{2}{R}{R}") == {
        "W": 0,
        "U": 0,
        "B": 0,
        "R": 2,
        "G": 0,
    }
    assert pips_from_mana_cost("{W}{U}")["W"] == 1
    assert pips_from_mana_cost("{W}{U}")["U"] == 1


def test_fill_basics_follows_color_pips_not_five_color():
    skeleton = [CardRef("Lightning Bolt")] * 40
    deck = fill_basics(
        skeleton,
        DeckConstraints(deck_size=60),
        color_pips={"W": 0, "U": 0, "B": 0, "R": 10, "G": 0},
    )
    names = [c.name for c in deck[40:]]
    assert names.count("Mountain") == 20
    assert names.count("Plains") == 0
    assert names.count("Island") == 0


def test_estimate_deck_color_pips_from_card_info():
    deck = [CardRef("Bolt"), CardRef("Counterspell")]
    info = {
        "Bolt": {"mana_cost": "{R}"},
        "Counterspell": {"mana_cost": "{U}{U}"},
    }
    pips = estimate_deck_color_pips(deck, card_info=info.get)
    assert pips["R"] == 1
    assert pips["U"] == 2
    assert pips["W"] == 0


def test_strip_basics():
    deck = [CardRef("Shock"), CardRef("Island"), CardRef("Mountain")]
    assert [c.name for c in strip_basics(deck)] == ["Shock"]
