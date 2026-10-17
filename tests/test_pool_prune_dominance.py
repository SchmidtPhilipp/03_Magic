# tests/test_pool_prune_dominance.py
from __future__ import annotations

from magic_optimizer.deck_picker.types import CardPool
from magic_optimizer.pool_prune.dominance import dominates, find_dominated, prune_superseded
from magic_optimizer.pool_prune.facts import CardFacts


def _creature(
    name: str,
    *,
    cmc: float,
    colors: set[str],
    power: float,
    toughness: float,
    keywords: set[str] | None = None,
) -> CardFacts:
    return CardFacts(
        name=name,
        cmc=cmc,
        type_line="Creature — Test",
        colors=frozenset(colors),
        power=power,
        toughness=toughness,
        keywords=frozenset(keywords or ()),
    )


def _instant(name: str, *, cmc: float, colors: set[str], keywords: set[str] | None = None) -> CardFacts:
    return CardFacts(
        name=name,
        cmc=cmc,
        type_line="Instant",
        colors=frozenset(colors),
        power=None,
        toughness=None,
        keywords=frozenset(keywords or ()),
    )


def test_creature_better_stats_same_cost_dominates():
    big = _creature("Big", cmc=2, colors={"G"}, power=3, toughness=3)
    small = _creature("Small", cmc=2, colors={"G"}, power=2, toughness=2)
    assert dominates(big, small)
    assert not dominates(small, big)


def test_lower_cmc_same_body_dominates():
    cheap = _creature("Cheap", cmc=1, colors={"R"}, power=2, toughness=1)
    pricey = _creature("Pricey", cmc=2, colors={"R"}, power=2, toughness=1)
    assert dominates(cheap, pricey)


def test_different_colors_do_not_dominate():
    g = _creature("Green", cmc=2, colors={"G"}, power=3, toughness=3)
    r = _creature("Red", cmc=2, colors={"R"}, power=2, toughness=2)
    assert not dominates(g, r)
    assert not dominates(r, g)


def test_different_type_buckets_do_not_dominate():
    bear = _creature("Bear", cmc=1, colors={"R"}, power=3, toughness=3)
    burn = _instant("Burn", cmc=1, colors={"R"})
    assert not dominates(bear, burn)


def test_star_power_skips_pair():
    star = CardFacts(
        name="Star",
        cmc=2,
        type_line="Creature — X",
        colors=frozenset({"B"}),
        power=None,
        toughness=2.0,
        keywords=frozenset(),
    )
    normal = _creature("Norm", cmc=2, colors={"B"}, power=2, toughness=2)
    assert not dominates(star, normal)
    assert not dominates(normal, star)


def test_find_and_prune():
    facts = {
        "Big": _creature("Big", cmc=2, colors={"G"}, power=3, toughness=3),
        "Small": _creature("Small", cmc=2, colors={"G"}, power=2, toughness=2),
        "Bolt": _instant("Bolt", cmc=1, colors={"R"}),
    }
    pool = CardPool({"Big": 4, "Small": 4, "Bolt": 4, "Plains": 20})
    supers = find_dominated(pool, facts)
    dropped = {s.dropped for s in supers}
    assert "Small" in dropped
    assert "Big" not in dropped
    pruned, report = prune_superseded(pool, facts)
    assert "Small" not in pruned.available
    assert pruned.available["Big"] == 4
    assert pruned.copies_available("Plains") > 0
    assert report["dropped_count"] >= 1
