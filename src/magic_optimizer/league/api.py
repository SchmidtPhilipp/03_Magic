# src/magic_optimizer/league/api.py
from __future__ import annotations

import random
from typing import Any

from flask import Blueprint, jsonify, request

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.trade import trade_report
from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.exporters.name_list import to_arena_text, to_copy_paste
from magic_optimizer.league.bootstrap import deck_from_policy, seed_league_from_pool
from magic_optimizer.league.job import OptimizationJob
from magic_optimizer.league.progress import snapshot_progress
from magic_optimizer.league.stop_policy import WinrateThresholdStop
from magic_optimizer.league.store import League
from magic_optimizer.league.types import JobState
from magic_optimizer.match_oracle.health import forge_available
from magic_optimizer.match_oracle.stub import StubMatchOracle

league_bp = Blueprint("league", __name__, url_prefix="/api/league")

_LEAGUE: League | None = None
_LAST_JOB_STATE: JobState | None = None


def reset_league() -> None:
    global _LEAGUE, _LAST_JOB_STATE
    _LEAGUE = None
    _LAST_JOB_STATE = None


def _get_league() -> League:
    global _LEAGUE
    if _LEAGUE is None:
        _LEAGUE = League()
    return _LEAGUE


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


def _oracle(backend: str = "stub", *, seed: int = 0):
    if backend == "forge" and forge_available():
        from magic_optimizer.match_oracle.forge import ForgeMatchOracle

        return ForgeMatchOracle()
    return StubMatchOracle(seed=seed)


def _standings_payload(league: League, k: int = 50) -> list[dict]:
    return [
        {
            "id": d.id,
            "elo": d.elo,
            "winrate": d.winrate,
            "wins": d.wins,
            "losses": d.losses,
            "games": d.games,
            "provenance": d.provenance,
        }
        for d in league.top(k)
    ]


@league_bp.route("/bootstrap", methods=["POST"])
def bootstrap():
    data, err = _parse_body()
    if data is None:
        return err
    pool, err = _parse_pool(data)
    if pool is None:
        return err
    try:
        n = int(data.get("n", 3))
    except (TypeError, ValueError):
        return jsonify({"error": "n must be an integer"}), 400
    seed = int(data.get("seed", 0))
    constraints = _parse_constraints(data)
    ratings = _parse_ratings(data)
    policy = HeuristicNextCardPolicy(ratings)
    league = League()
    ids = seed_league_from_pool(
        league, policy, pool, constraints, n=n, rng=random.Random(seed)
    )
    global _LEAGUE
    _LEAGUE = league
    return jsonify({"deck_ids": ids, "size": len(league)})


@league_bp.route("/challenge", methods=["POST"])
def challenge():
    data, err = _parse_body()
    if data is None:
        return err
    deck_raw = data.get("deck")
    if not isinstance(deck_raw, list) or not all(isinstance(x, str) for x in deck_raw):
        return jsonify({"error": "deck must be a list of strings"}), 400
    league = _get_league()
    if len(league) == 0:
        return jsonify({"error": "league is empty; bootstrap first"}), 400
    games = int(data.get("games", 5))
    backend = str(data.get("backend", "stub"))
    seed = int(data.get("seed", 0))
    stop_cfg = data.get("stop") or {}
    stop = WinrateThresholdStop(
        threshold=float(stop_cfg.get("threshold", 0.55)),
        min_games=int(stop_cfg.get("min_games", 20)),
    )
    job = OptimizationJob(
        league,
        _oracle(backend, seed=seed),
        stop,
        games_per_match=games,
        seed=seed,
    )
    try:
        summary = job.challenge(list(deck_raw), deck_id=data.get("deck_id"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    global _LAST_JOB_STATE
    _LAST_JOB_STATE = job.state
    return jsonify(summary)


@league_bp.route("/progress", methods=["GET"])
def progress():
    league = _get_league()
    return jsonify(snapshot_progress(_LAST_JOB_STATE, league).to_dict())


@league_bp.route("/trade-report", methods=["POST"])
def trade_report_endpoint():
    data, err = _parse_body()
    if data is None:
        return err
    deck = data.get("deck")
    owned_raw = data.get("owned")
    if not isinstance(deck, list) or not all(isinstance(x, str) for x in deck):
        return jsonify({"error": "deck must be a list of strings"}), 400
    if not isinstance(owned_raw, dict):
        return jsonify({"error": "owned must be an object"}), 400
    available: dict[str, int] = {}
    for name, qty in owned_raw.items():
        try:
            available[str(name)] = int(qty)
        except (TypeError, ValueError):
            return jsonify({"error": f"owned quantity for {name!r} must be an integer"}), 400
    return jsonify(trade_report(list(deck), CardPool(available)))


@league_bp.route("/export", methods=["POST"])
def export_deck():
    data, err = _parse_body()
    if data is None:
        return err
    deck = data.get("deck")
    fmt = str(data.get("format", "arena"))
    if not isinstance(deck, list) or not all(isinstance(x, str) for x in deck):
        return jsonify({"error": "deck must be a list of strings"}), 400
    title = str(data.get("title", ""))
    if fmt == "arena":
        text = to_arena_text(list(deck), title=title)
    elif fmt == "copy_paste":
        text = to_copy_paste(list(deck))
    else:
        return jsonify({"error": "format must be 'arena' or 'copy_paste'"}), 400
    return jsonify({"text": text, "format": fmt})


@league_bp.route("/standings", methods=["GET"])
def standings():
    if request.args.get("reset") in ("1", "true", "yes"):
        reset_league()
        return jsonify({"standings": []})
    league = _get_league()
    return jsonify({"standings": _standings_payload(league), "size": len(league)})


@league_bp.route("/run", methods=["POST"])
def run():
    data, err = _parse_body()
    if data is None:
        return err
    pool, err = _parse_pool(data)
    if pool is None:
        return err
    constraints = _parse_constraints(data)
    ratings = _parse_ratings(data)
    policy = HeuristicNextCardPolicy(ratings)
    n = int(data.get("n", 3))
    seed = int(data.get("seed", 0))
    max_challenges = int(data.get("max_challenges", 10))
    games = int(data.get("games", 5))
    backend = str(data.get("backend", "stub"))
    stop_cfg = data.get("stop") or {}
    stop = WinrateThresholdStop(
        threshold=float(stop_cfg.get("threshold", 0.55)),
        min_games=int(stop_cfg.get("min_games", 20)),
    )

    league = League()
    seed_league_from_pool(
        league, policy, pool, constraints, n=n, rng=random.Random(seed)
    )
    global _LEAGUE
    _LEAGUE = league

    rng = random.Random(seed + 1)
    counter = {"i": 0}

    def build() -> list[str]:
        counter["i"] += 1
        jittered = {
            name: score + rng.uniform(-1.0, 1.0) for name, score in ratings.items()
        }
        return deck_from_policy(
            HeuristicNextCardPolicy(jittered), pool, constraints
        )

    job = OptimizationJob(
        league,
        _oracle(backend, seed=seed),
        stop,
        games_per_match=games,
        seed=seed,
    )
    state = job.run_until_stop(build, max_challenges=max_challenges)
    global _LAST_JOB_STATE
    _LAST_JOB_STATE = state
    return jsonify(
        {
            "job_state": {
                "best_deck_id": state.best_deck_id,
                "best_winrate": state.best_winrate,
                "games_vs_top": state.games_vs_top,
                "challenges": state.challenges,
                "elo_history": state.elo_history,
            },
            "standings": _standings_payload(league),
            "size": len(league),
        }
    )
