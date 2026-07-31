# src/magic_optimizer/selfplay/api.py
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.league.stop_policy import WinrateThresholdStop
from magic_optimizer.selfplay.loop import SelfPlayLoop
from magic_optimizer.selfplay.oracle_factory import make_oracle

selfplay_bp = Blueprint("selfplay", __name__, url_prefix="/api/selfplay")

_LAST_RESULT: dict[str, Any] | None = None


def reset_selfplay() -> None:
    global _LAST_RESULT
    _LAST_RESULT = None


def _parse_body() -> tuple[dict | None, tuple]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "invalid JSON"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "request body must be a JSON object"}), 400)
    return data, ()


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


def _parse_ratings(data: dict) -> dict[str, float]:
    ratings_raw = data.get("ratings") or {}
    if not isinstance(ratings_raw, dict):
        return {}
    out: dict[str, float] = {}
    for name, score in ratings_raw.items():
        try:
            out[str(name)] = float(score)
        except (TypeError, ValueError):
            continue
    return out


def _parse_constraints(data: dict) -> DeckConstraints:
    kwargs: dict[str, Any] = {}
    banned_raw = data.get("banned") or []
    if isinstance(banned_raw, (list, tuple)):
        kwargs["banned"] = frozenset(str(n) for n in banned_raw)
    pinned_raw = data.get("pinned") or []
    if isinstance(pinned_raw, (list, tuple)):
        kwargs["pinned"] = tuple(str(n) for n in pinned_raw)
    for field in ("deck_size", "max_copies", "non_basic_target"):
        if field in data:
            try:
                kwargs[field] = int(data[field])
            except (TypeError, ValueError):
                pass
    return DeckConstraints(**kwargs)


@selfplay_bp.route("/run", methods=["POST"])
def run_selfplay():
    data, err = _parse_body()
    if data is None:
        return err
    pool, err = _parse_pool(data)
    if pool is None:
        return err
    backend = str(data.get("backend", "stub"))
    try:
        oracle = make_oracle(backend=backend, seed=int(data.get("seed", 0)))
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    stop_cfg = data.get("stop") or {}
    stop = WinrateThresholdStop(
        threshold=float(stop_cfg.get("threshold", 0.55)),
        min_games=int(stop_cfg.get("min_games", 20)),
    )
    loop = SelfPlayLoop(
        oracle=oracle,
        stop_policy=stop,
        pool=pool,
        constraints=_parse_constraints(data),
        ratings=_parse_ratings(data),
        records_path=data.get("records_path"),
        games_per_match=int(data.get("games", 5)),
        seed=int(data.get("seed", 0)),
        retrain_every=int(data.get("retrain_every", 2)),
        dim=int(data.get("dim", 64)),
    )
    result = loop.run(
        bootstrap_n=int(data.get("bootstrap_n", 3)),
        max_challenges=int(data.get("max_challenges", 20)),
    )
    global _LAST_RESULT
    _LAST_RESULT = result
    return jsonify(result)


@selfplay_bp.route("/last", methods=["GET"])
def last_result():
    if _LAST_RESULT is None:
        return jsonify({"error": "no selfplay run yet"}), 404
    return jsonify(_LAST_RESULT)
