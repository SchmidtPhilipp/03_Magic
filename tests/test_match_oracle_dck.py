from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.dck import to_dck


def test_to_dck_aggregates():
    deck = [CardRef("Shock"), CardRef("Shock"), CardRef("Island")]
    text = to_dck(deck, name="Test")
    assert "Name=Test" in text
    assert "[Main]" in text
    assert "2 Shock" in text
    assert "1 Island" in text


def test_to_dck_skips_empty_names():
    deck = [CardRef("Shock"), CardRef("   ")]
    text = to_dck(deck)
    assert "1 Shock" in text
    main_lines = text.split("[Main]", 1)[1].strip().splitlines()
    assert main_lines == ["1 Shock"]


def test_to_dck_default_name():
    text = to_dck([CardRef("Island")])
    assert "Name=Deck" in text
