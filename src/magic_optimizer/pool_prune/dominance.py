# src/magic_optimizer/pool_prune/dominance.py
from __future__ import annotations

from dataclasses import dataclass

from magic_optimizer.deck_picker.types import BASIC_LANDS, CardPool
from magic_optimizer.pool_prune.facts import CardFacts, type_bucket


@dataclass(frozen=True)
class Supersession:
    kept: str
    dropped: str
    reason: str


def dominates(a: CardFacts, b: CardFacts) -> bool:
    """Return True if card a strictly dominates card b under MVP rules."""
    if a.name == b.name:
        return False
    if a.name in BASIC_LANDS or b.name in BASIC_LANDS:
        return False

    bucket_a = type_bucket(a.type_line)
    bucket_b = type_bucket(b.type_line)
    if bucket_a != bucket_b or bucket_a == "other":
        return False

    if a.cmc > b.cmc:
        return False
    if not a.colors.issubset(b.colors):
        return False
    if not b.keywords.issubset(a.keywords):
        return False

    creature = bucket_a == "creature"
    if creature:
        if a.power is None or a.toughness is None or b.power is None or b.toughness is None:
            return False
        if a.power < b.power or a.toughness < b.toughness:
            return False

    better_cmc = a.cmc < b.cmc
    better_kw = len(a.keywords) > len(b.keywords)
    better_body = False
    if creature:
        better_body = a.power > b.power or a.toughness > b.toughness

    return better_cmc or better_kw or better_body


def find_dominated(
    pool: CardPool,
    facts: dict[str, CardFacts],
) -> list[Supersession]:
    names = [
        n
        for n, qty in pool.available.items()
        if qty > 0 and n not in BASIC_LANDS and n in facts
    ]
    out: list[Supersession] = []
    dropped: set[str] = set()
    for kept_name in names:
        if kept_name in dropped:
            continue
        kept = facts[kept_name]
        for drop_name in names:
            if drop_name == kept_name or drop_name in dropped:
                continue
            other = facts[drop_name]
            if dominates(kept, other):
                reason = (
                    f"{kept_name} dominates {drop_name} "
                    f"(bucket={type_bucket(kept.type_line)}, "
                    f"cmc {kept.cmc}<={other.cmc})"
                )
                out.append(
                    Supersession(kept=kept_name, dropped=drop_name, reason=reason)
                )
                dropped.add(drop_name)
    out.sort(key=lambda s: (s.dropped, s.kept))
    return out


def prune_superseded(
    pool: CardPool,
    facts: dict[str, CardFacts],
) -> tuple[CardPool, dict]:
    supers = find_dominated(pool, facts)
    drop = {s.dropped for s in supers}
    available = {
        name: qty
        for name, qty in pool.available.items()
        if name not in drop
    }
    pruned = CardPool(available)
    report = {
        "dropped_count": len(drop),
        "kept_pool_size": len(available),
        "original_pool_size": len(pool.available),
        "supersessions": [
            {"kept": s.kept, "dropped": s.dropped, "reason": s.reason} for s in supers
        ],
    }
    return pruned, report
