# tests/test_deck_picker_color_limit.py
from magic_optimizer.deck_picker.colors import (
    card_fits_color_constraints,
    deck_color_identity,
)
from magic_optimizer.deck_picker.complete import complete_deck
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
)


def _info(name: str) -> dict | None:
    table = {
        "Lightning Bolt": {"color_identity": ["R"], "mana_cost": "{R}"},
        "Counterspell": {"color_identity": ["U"], "mana_cost": "{U}{U}"},
        "Dark Ritual": {"color_identity": ["B"], "mana_cost": "{B}"},
        "Swords to Plowshares": {"color_identity": ["W"], "mana_cost": "{W}"},
        "Llanowar Elves": {"color_identity": ["G"], "mana_cost": "{G}"},
        "Terminate": {"color_identity": ["B", "R"], "mana_cost": "{B}{R}"},
        "Sol Ring": {"color_identity": [], "mana_cost": "{1}"},
    }
    return table.get(name)


def test_max_colors_two_blocks_third_color():
    deck = [CardRef("Lightning Bolt"), CardRef("Terminate")]
    constraints = DeckConstraints(max_colors=2)
    assert card_fits_color_constraints(
        "Dark Ritual", deck, constraints, card_info=_info
    )
    assert not card_fits_color_constraints(
        "Counterspell", deck, constraints, card_info=_info
    )
    assert card_fits_color_constraints(
        "Sol Ring", deck, constraints, card_info=_info
    )


def test_allowed_colors_hard_lock():
    constraints = DeckConstraints(allowed_colors=frozenset({"U", "R"}))
    assert card_fits_color_constraints(
        "Lightning Bolt", [], constraints, card_info=_info
    )
    assert not card_fits_color_constraints(
        "Dark Ritual", [], constraints, card_info=_info
    )
    assert not card_fits_color_constraints(
        "Terminate", [], constraints, card_info=_info
    )  # needs B


def test_unknown_card_fails_closed_with_card_info():
    constraints = DeckConstraints(max_colors=3)
    assert not card_fits_color_constraints(
        "Totally Fake Card", [], constraints, card_info=_info
    )


def test_complete_deck_respects_max_colors_three():
    pool = CardPool(
        {
            "Lightning Bolt": 4,
            "Counterspell": 4,
            "Dark Ritual": 4,
            "Swords to Plowshares": 4,
            "Llanowar Elves": 4,
            "Terminate": 4,
            "Sol Ring": 4,
        }
    )
    # Establish R first, then B (Terminate), stay ≤3 — bury W/G/U ratings.
    ratings = {
        "Lightning Bolt": 100.0,
        "Terminate": 90.0,
        "Dark Ritual": 80.0,
        "Sol Ring": 70.0,
        "Swords to Plowshares": 1.0,
        "Llanowar Elves": 1.0,
        "Counterspell": 1.0,
    }
    constraints = DeckConstraints(non_basic_target=16, max_colors=3, max_copies=4)
    policy = HeuristicNextCardPolicy(ratings)
    deck = complete_deck(policy, pool, constraints, card_info=_info)
    ci = deck_color_identity(deck, card_info=_info)
    assert ci <= frozenset({"R", "B"}) or len(ci) <= 3
    assert "W" not in ci or "U" not in ci or "G" not in ci
    # With these ratings should lock BR (± colorless)
    assert ci == frozenset({"B", "R"})
    assert sum(1 for c in deck if c.name not in BASIC_LANDS) == 16
    basics = {c.name for c in deck if c.name in BASIC_LANDS}
    assert basics <= {"Mountain", "Swamp"}
    assert "Plains" not in basics and "Island" not in basics and "Forest" not in basics
