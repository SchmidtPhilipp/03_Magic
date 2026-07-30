from __future__ import annotations

from flask import Blueprint, jsonify, request

from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.forge import ForgeMatchOracle
from magic_optimizer.match_oracle.health import forge_available
from magic_optimizer.match_oracle.stub import StubMatchOracle
from magic_optimizer.match_oracle.types import MatchResult

match_oracle_bp = Blueprint(
    "match_oracle",
    __name__,
    url_prefix="/api/match-oracle",
)

MAX_GAMES = 100


def _result_to_json(result: MatchResult) -> dict:
    return {
        "wins_a": result.wins_a,
        "wins_b": result.wins_b,
        "games_played": result.games_played,
        "void_games": result.void_games,
        "engine": result.engine,
        "winrate_a": result.winrate_a,
        "details": result.details,
    }


def _parse_body() -> tuple[dict | None, tuple]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "invalid JSON"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "request body must be a JSON object"}), 400)
    return data, ()


def _parse_deck(data: dict, field: str) -> tuple[list[CardRef] | None, tuple]:
    if field not in data:
        return None, (jsonify({"error": f"{field} required"}), 400)
    deck_raw = data[field]
    if not isinstance(deck_raw, list):
        return None, (jsonify({"error": f"{field} must be a list"}), 400)
    for item in deck_raw:
        if not isinstance(item, str):
            return None, (
                jsonify({"error": f"{field} entries must be strings"}),
                400,
            )
    return [CardRef(name) for name in deck_raw], ()


def _parse_games(data: dict) -> tuple[int | None, tuple]:
    if "games" not in data:
        return None, (jsonify({"error": "games required"}), 400)
    try:
        games = int(data["games"])
    except (TypeError, ValueError):
        return None, (jsonify({"error": "games must be an integer"}), 400)
    if games < 1:
        return None, (jsonify({"error": "games must be at least 1"}), 400)
    if games > MAX_GAMES:
        return None, (
            jsonify({"error": f"games must be at most {MAX_GAMES}"}),
            400,
        )
    return games, ()


def _parse_backend(data: dict) -> tuple[str | None, tuple]:
    backend = data.get("backend", "stub")
    if backend not in ("stub", "forge"):
        return None, (jsonify({"error": "backend must be 'stub' or 'forge'"}), 400)
    return backend, ()


@match_oracle_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"forge_available": forge_available()})


@match_oracle_bp.route("/play", methods=["POST"])
def play():
    data, err = _parse_body()
    if data is None:
        return err

    deck_a, err = _parse_deck(data, "deck_a")
    if deck_a is None:
        return err
    deck_b, err = _parse_deck(data, "deck_b")
    if deck_b is None:
        return err
    games, err = _parse_games(data)
    if games is None:
        return err
    backend, err = _parse_backend(data)
    if backend is None:
        return err

    if backend == "forge":
        if not forge_available():
            return jsonify({"error": "forge backend unavailable"}), 503
        try:
            oracle = ForgeMatchOracle()
        except RuntimeError as exc:
            msg = str(exc)
            if "FORGE_JAR" in msg or "FORGE_TIMEOUT_SEC" in msg or "timeout_sec" in msg:
                return jsonify({"error": msg}), 503
            raise
    else:
        oracle = StubMatchOracle()

    result = oracle.play(deck_a, deck_b, games=games)
    return jsonify(_result_to_json(result))
