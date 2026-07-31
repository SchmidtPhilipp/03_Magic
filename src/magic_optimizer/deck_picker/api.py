# src/magic_optimizer/deck_picker/api.py
from __future__ import annotations

from flask import Blueprint, jsonify, request

from magic_optimizer.deck_picker.checkpoint import (
    DeckRLState,
    state_from_dict,
    state_to_dict,
)
from magic_optimizer.deck_picker.complete import (
    complete_deck,
    complete_deck_with_trajectory,
)
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.missing import missing_cards
from magic_optimizer.deck_picker.modify import apply_swap, propose_swaps
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
    want_trajectory = bool(data.get("trajectory", False))
    if want_trajectory:
        deck, steps = complete_deck_with_trajectory(
            policy, pool, constraints, seed_deck=decklist
        )
    else:
        deck = complete_deck(policy, pool, constraints, seed_deck=decklist)
        steps = []

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

    payload: dict = {
        "deck": [card.name for card in deck],
        "missing": missing,
    }
    if want_trajectory:
        payload["trajectory"] = [
            {
                "action": step.action,
                "card": step.card.name,
                "score": step.score,
                "index": step.index,
                "alternatives": [
                    {"name": a.card.name, "score": a.score} for a in step.alternatives
                ],
            }
            for step in steps
        ]
        payload["checkpoint"] = state_to_dict(
            DeckRLState(
                deck=deck,
                pool=dict(pool.available),
                constraints=constraints,
                ratings=ratings,
                iteration=0,
                trajectory=payload["trajectory"],
                meta={"source": "complete"},
            )
        )
    return jsonify(payload)


@deck_picker_bp.route("/modify", methods=["POST"])
def modify():
    """Propose (and optionally apply) swaps for an existing decklist."""
    data, err = _parse_body()
    if data is None:
        return err

    pool, err = _parse_pool(data)
    if pool is None:
        return err
    decklist, err = _parse_decklist(data)
    if decklist is None:
        return err
    if not decklist:
        return jsonify({"error": "decklist required"}), 400
    constraints, err = _parse_constraints(data)
    if constraints is None:
        return err
    ratings, err = _parse_ratings(data)
    if ratings is None:
        return err

    try:
        k = int(data.get("k", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "k must be an integer"}), 400

    policy = HeuristicNextCardPolicy(ratings)
    swaps = propose_swaps(policy, pool, decklist, constraints, k=k)
    payload: dict = {
        "swaps": [
            {
                "remove": s.remove.name,
                "add": s.add.name,
                "score_delta": s.score_delta,
                "remove_score": s.remove_score,
                "add_score": s.add_score,
            }
            for s in swaps
        ]
    }

    if data.get("apply") and swaps:
        try:
            n = int(data.get("apply_count", 1))
        except (TypeError, ValueError):
            return jsonify({"error": "apply_count must be an integer"}), 400
        updated = list(decklist)
        applied = []
        for proposal in swaps[: max(0, n)]:
            updated = apply_swap(updated, proposal)
            applied.append(
                {"remove": proposal.remove.name, "add": proposal.add.name}
            )
        payload["deck"] = [c.name for c in updated]
        payload["applied"] = applied

    return jsonify(payload)


@deck_picker_bp.route("/resume", methods=["POST"])
def resume():
    """
    Resume deck RL loop from a checkpoint body.

    Body: {"checkpoint": {...}, "apply": true, "apply_count": 1, "k": 5}
    Returns updated checkpoint + swaps/applied.
    """
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "invalid JSON object"}), 400
    raw = data.get("checkpoint")
    if not isinstance(raw, dict):
        return jsonify({"error": "checkpoint object required"}), 400
    try:
        state = state_from_dict(raw)
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": f"invalid checkpoint: {exc}"}), 400

    try:
        k = int(data.get("k", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "k must be an integer"}), 400

    policy = HeuristicNextCardPolicy(state.ratings)
    pool = state.card_pool()
    swaps = propose_swaps(policy, pool, state.deck, state.constraints, k=k)
    payload: dict = {
        "swaps": [
            {
                "remove": s.remove.name,
                "add": s.add.name,
                "score_delta": s.score_delta,
                "remove_score": s.remove_score,
                "add_score": s.add_score,
            }
            for s in swaps
        ],
        "iteration": state.iteration,
    }

    if data.get("apply") and swaps:
        try:
            n = int(data.get("apply_count", 1))
        except (TypeError, ValueError):
            return jsonify({"error": "apply_count must be an integer"}), 400
        updated = list(state.deck)
        applied = []
        for proposal in swaps[: max(0, n)]:
            updated = apply_swap(updated, proposal)
            applied.append(
                {"remove": proposal.remove.name, "add": proposal.add.name}
            )
            state.trajectory.append(
                {
                    "action": "swap",
                    "remove": proposal.remove.name,
                    "add": proposal.add.name,
                    "score_delta": proposal.score_delta,
                }
            )
        state.deck = updated
        state.iteration += len(applied)
        payload["applied"] = applied

    payload["checkpoint"] = state_to_dict(state)
    payload["deck"] = [c.name for c in state.deck]
    return jsonify(payload)
