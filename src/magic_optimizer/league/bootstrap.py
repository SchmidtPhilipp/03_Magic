# src/magic_optimizer/league/bootstrap.py
from __future__ import annotations

import random
import uuid
from collections.abc import Callable

from magic_optimizer.deck_picker.complete import complete_deck
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy, NextCardPolicy
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints
from magic_optimizer.league.store import League
from magic_optimizer.league.types import LeagueDeck


def deck_from_policy(
    policy: NextCardPolicy,
    pool: CardPool,
    constraints: DeckConstraints,
    *,
    seed_deck: list[CardRef] | None = None,
    color_pips: dict[str, int] | None = None,
    card_info: Callable[[str], dict | None] | None = None,
) -> list[str]:
    """Build a full deck via complete_deck; return card names."""
    deck = complete_deck(
        policy,
        pool,
        constraints,
        seed_deck=seed_deck,
        color_pips=color_pips,
        card_info=card_info,
    )
    return [c.name for c in deck]


def seed_league_from_pool(
    league: League,
    policy: HeuristicNextCardPolicy,
    pool: CardPool,
    constraints: DeckConstraints,
    *,
    n: int,
    rng: random.Random,
    color_pips: dict[str, int] | None = None,
    card_info: Callable[[str], dict | None] | None = None,
    provenance: str = "bootstrap",
    id_prefix: str | None = None,
) -> list[str]:
    """Add n decks built with jittered rating copies of policy; return ids."""
    base = dict(getattr(policy, "_ratings", {}) or {})
    prefix = id_prefix or provenance.split(":")[0] or "boot"
    ids: list[str] = []
    for i in range(max(0, n)):
        jittered = {
            name: score + rng.uniform(-1.0, 1.0) for name, score in base.items()
        }
        child = HeuristicNextCardPolicy(
            jittered,
            synergy=getattr(policy, "_synergy", None),
            synergy_scale=float(getattr(policy, "_synergy_scale", 0.1)),
        )
        cards = deck_from_policy(
            child,
            pool,
            constraints,
            color_pips=color_pips,
            card_info=card_info,
        )
        deck_id = f"{prefix}-{i}-{uuid.uuid4().hex[:8]}"
        league.add(
            LeagueDeck(
                id=deck_id,
                cards=cards,
                elo=1000.0 + rng.uniform(-20.0, 20.0),
                provenance=provenance,
            )
        )
        ids.append(deck_id)
    return ids
