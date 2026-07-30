# src/magic_optimizer/deck_picker/api.py
from __future__ import annotations

from flask import Blueprint, jsonify, request

from magic_optimizer.deck_picker.complete import complete_deck
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.missing import missing_cards
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints

deck_picker_bp = Blueprint(
    "deck_picker",
    __name__,
    url_prefix="/api/deck-picker",
)


def _parse_pool(data: dict) -> CardPool | None:
    pool_raw = data.get("pool")
    if not isinstance(pool_raw, dict):
        return None
    available = {str(name): int(qty) for name, qty in pool_raw.items()}
    return CardPool(available)


def _parse_decklist(data: dict) -> list[CardRef]:
    decklist = data.get("decklist") or []
    return [CardRef(str(name)) for name in decklist]


def _parse_constraints(data: dict) -> DeckConstraints:
    banned = frozenset(str(name) for name in (data.get("banned") or []))
    pinned = tuple(str(name) for name in (data.get("pinned") or []))
    kwargs: dict = {"banned": banned, "pinned": pinned}
    if "deck_size" in data:
        kwargs["deck_size"] = int(data["deck_size"])
    if "max_copies" in data:
        kwargs["max_copies"] = int(data["max_copies"])
    if "non_basic_target" in data:
        kwargs["non_basic_target"] = int(data["non_basic_target"])
    return DeckConstraints(**kwargs)


def _parse_ratings(data: dict) -> dict[str, float]:
    ratings_raw = data.get("ratings") or {}
    return {str(name): float(score) for name, score in ratings_raw.items()}


def _parse_body() -> tuple[dict | None, tuple]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "invalid JSON"}), 400)
    pool = _parse_pool(data)
    if pool is None:
        return None, (jsonify({"error": "pool required"}), 400)
    return data, ()


@deck_picker_bp.route("/next-card", methods=["POST"])
def next_card():
    data, err = _parse_body()
    if data is None:
        return err

    pool = _parse_pool(data)
    assert pool is not None
    decklist = _parse_decklist(data)
    constraints = _parse_constraints(data)
    ratings = _parse_ratings(data)
    k = int(data.get("k", 10))

    policy = HeuristicNextCardPolicy(ratings)
    scored = policy.next_card(pool, decklist, constraints, k=k)
    return jsonify(
        {
            "candidates": [
                {"name": item.card.name, "score": item.score} for item in scored
            ]
        }
    )


@deck_picker_bp.route("/complete", methods=["POST"])
def complete():
    data, err = _parse_body()
    if data is None:
        return err

    pool = _parse_pool(data)
    assert pool is not None
    decklist = _parse_decklist(data)
    constraints = _parse_constraints(data)
    ratings = _parse_ratings(data)

    policy = HeuristicNextCardPolicy(ratings)
    deck = complete_deck(policy, pool, constraints, seed_deck=decklist)

    owned_raw = data.get("owned")
    if isinstance(owned_raw, dict):
        owned = CardPool({str(name): int(qty) for name, qty in owned_raw.items()})
        missing = [[name, qty] for name, qty in missing_cards(deck, owned)]
    else:
        missing = []

    return jsonify({"deck": [card.name for card in deck], "missing": missing})
