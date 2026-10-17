# tests/test_synergy_graph.py
from __future__ import annotations

from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.synergy.graph import SynergyGraph, bonus_for_candidate


def test_add_deck_builds_edges():
    g = SynergyGraph()
    g.add_deck(["Shock", "Bolt", "Mountain"], weight=1.0)
    assert g.score_pair("Shock", "Bolt") == 1.0
    assert g.score_pair("Bolt", "Shock") == 1.0
    # Basics ignored
    assert g.score_pair("Shock", "Mountain") == 0.0


def test_bonus_for_candidate_mean_edges():
    g = SynergyGraph()
    g.add_deck(["Shock", "Bolt"], weight=2.0)
    g.add_deck(["Shock", "Lava Spike"], weight=0.0)
    deck = [CardRef("Shock")]
    bonus = bonus_for_candidate(g, deck, "Bolt")
    assert bonus == 2.0
    assert bonus_for_candidate(g, deck, "Unknown") == 0.0
