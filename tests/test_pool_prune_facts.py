# tests/test_pool_prune_facts.py
from __future__ import annotations

from pathlib import Path

from magic_optimizer.pool_prune.facts import (
    CardFacts,
    CardFactsStore,
    facts_from_scryfall_dict,
    parse_stat,
    type_bucket,
)


def test_facts_from_scryfall_creature():
    data = {
        "name": "Grizzly Bears",
        "cmc": 2.0,
        "type_line": "Creature — Bear",
        "color_identity": ["G"],
        "colors": ["G"],
        "power": "2",
        "toughness": "2",
        "keywords": ["Reach"],
    }
    facts = facts_from_scryfall_dict(data)
    assert facts.name == "Grizzly Bears"
    assert facts.cmc == 2.0
    assert facts.colors == frozenset({"G"})
    assert facts.power == 2.0
    assert facts.toughness == 2.0
    assert "Reach" in facts.keywords
    assert type_bucket(facts.type_line) == "creature"


def test_parse_star_power_is_none():
    assert parse_stat("*") is None
    assert parse_stat(None) is None
    assert parse_stat("3") == 3.0


def test_store_uses_cache_and_lookup(tmp_path: Path):
    calls: list[str] = []

    def lookup(name: str) -> dict | None:
        calls.append(name)
        return {
            "name": name,
            "cmc": 1.0,
            "type_line": "Instant",
            "color_identity": ["R"],
            "power": None,
            "toughness": None,
            "keywords": [],
        }

    cache = tmp_path / "facts.json"
    store = CardFactsStore(cache_path=cache, lookup=lookup)
    a = store.get_many(["Shock", "Bolt"])
    assert set(a) == {"Shock", "Bolt"}
    assert len(calls) == 2
    # Second call hits disk/memory cache
    b = store.get_many(["Shock"])
    assert b["Shock"].cmc == 1.0
    assert calls == ["Shock", "Bolt"]
    assert cache.exists()


def test_card_facts_roundtrip_dict():
    f = CardFacts(
        name="X",
        cmc=1.0,
        type_line="Instant",
        colors=frozenset({"R"}),
        power=None,
        toughness=None,
        keywords=frozenset(),
    )
    restored = CardFacts.from_dict(f.to_dict())
    assert restored == f
