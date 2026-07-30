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


def _parse_pool(data: dict) -> tuple[CardPool | None, tuple]:
    pool_raw = data.get("pool")
    if pool_raw is None:
        return None, (jsonify({"error": "pool required"}), 400)
    if not isinstance(pool_raw, dict):
        return None, (jsonify({"error": "pool must be an object"}), 400)
    available: dict[str, int] = {}
    for name, qty in pool_raw.items():
        try:
            available[str(name)] = int(qty)
        except (TypeError, ValueError):
            return None, (
                jsonify({"error": f"pool quantity for {name!r} must be an integer"}),
                400,
            )
    return CardPool(available), ()


def _parse_decklist(data: dict) -> tuple[list[CardRef] | None, tuple]:
    decklist_raw = data.get("decklist", [])
    if decklist_raw is None:
        decklist_raw = []
    if not isinstance(decklist_raw, list):
        return None, (jsonify({"error": "decklist must be a list"}), 400)
    for item in decklist_raw:
        if not isinstance(item, str):
            return None, (jsonify({"error": "decklist entries must be strings"}), 400)
    return [CardRef(name) for name in decklist_raw], ()


def _parse_constraints(data: dict) -> tuple[DeckConstraints | None, tuple]:
    banned_raw = data.get("banned") or []
    if not isinstance(banned_raw, (list, tuple)):
        return None, (jsonify({"error": "banned must be a list"}), 400)
    pinned_raw = data.get("pinned") or []
    if not isinstance(pinned_raw, (list, tuple)):
        return None, (jsonify({"error": "pinned must be a list"}), 400)

    kwargs: dict = {
        "banned": frozenset(str(name) for name in banned_raw),
        "pinned": tuple(str(name) for name in pinned_raw),
    }
    for field in ("deck_size", "max_copies", "non_basic_target"):
        if field in data:
            try:
                kwargs[field] = int(data[field])
            except (TypeError, ValueError):
                return None, (jsonify({"error": f"{field} must be an integer"}), 400)
    return DeckConstraints(**kwargs), ()


def _parse_ratings(data: dict) -> tuple[dict[str, float] | None, tuple]:
    ratings_raw = data.get("ratings") or {}
    if not isinstance(ratings_raw, dict):
        return None, (jsonify({"error": "ratings must be an object"}), 400)
    ratings: dict[str, float] = {}
    for name, score in ratings_raw.items():
        try:
            ratings[str(name)] = float(score)
        except (TypeError, ValueError):
            return None, (
                jsonify({"error": f"rating for {name!r} must be a number"}),
                400,
            )
    return ratings, ()


def _parse_body() -> tuple[dict | None, tuple]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "invalid JSON"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "request body must be a JSON object"}), 400)
    pool, err = _parse_pool(data)
    if pool is None:
        return None, err
    return data, ()


@deck_picker_bp.route("/next-card", methods=["POST"])
def next_card():
    data, err = _parse_body()
    if data is None:
        return err

    pool, err = _parse_pool(data)
    if pool is None:
        return err
    decklist, err = _parse_decklist(data)
    if decklist is None:
        return err
    constraints, err = _parse_constraints(data)
    if constraints is None:
        return err
    ratings, err = _parse_ratings(data)
    if ratings is None:
        return err

    try:
        k = int(data.get("k", 10))
    except (TypeError, ValueError):
        return jsonify({"error": "k must be an integer"}), 400

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

    pool, err = _parse_pool(data)
    if pool is None:
        return err
    decklist, err = _parse_decklist(data)
    if decklist is None:
        return err
    constraints, err = _parse_constraints(data)
    if constraints is None:
        return err
    ratings, err = _parse_ratings(data)
    if ratings is None:
        return err

    policy = HeuristicNextCardPolicy(ratings)
    deck = complete_deck(policy, pool, constraints, seed_deck=decklist)

    owned_raw = data.get("owned")
    if isinstance(owned_raw, dict):
        owned_available: dict[str, int] = {}
        for name, qty in owned_raw.items():
            try:
                owned_available[str(name)] = int(qty)
            except (TypeError, ValueError):
                return (
                    jsonify({"error": f"owned quantity for {name!r} must be an integer"}),
                    400,
                )
        owned = CardPool(owned_available)
        missing = [[name, qty] for name, qty in missing_cards(deck, owned)]
    else:
        missing = []

    return jsonify({"deck": [card.name for card in deck], "missing": missing})
