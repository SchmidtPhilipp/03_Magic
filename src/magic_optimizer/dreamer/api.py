# src/magic_optimizer/dreamer/api.py
from __future__ import annotations

from flask import Blueprint, jsonify, request

from magic_optimizer.dreamer.imagine import score_deck_vs_opponents
from magic_optimizer.dreamer.replay import ReplayBuffer
from magic_optimizer.dreamer.world_model import WorldModel

dreamer_bp = Blueprint("dreamer", __name__, url_prefix="/api/dreamer")

_MODEL: WorldModel | None = None


def reset_dreamer() -> None:
    global _MODEL
    _MODEL = None


def _get_model(*, dim: int = 64, seed: int = 0) -> WorldModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = WorldModel(dim=dim, seed=seed)
    return _MODEL


def _parse_body() -> tuple[dict | None, tuple]:
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "invalid JSON"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "request body must be a JSON object"}), 400)
    return data, ()


@dreamer_bp.route("/train", methods=["POST"])
def train():
    data, err = _parse_body()
    if data is None:
        return err
    records = data.get("records")
    if not isinstance(records, list):
        return jsonify({"error": "records must be a list"}), 400
    dim = int(data.get("dim", 64))
    seed = int(data.get("seed", 0))
    buf = ReplayBuffer()
    n = buf.extend_from_records(records)
    model = WorldModel(dim=dim, seed=seed)
    stats = model.fit(buf)
    global _MODEL
    _MODEL = model
    return jsonify({"loss": stats["loss"], "n": int(stats["n"]), "added": n})


@dreamer_bp.route("/score", methods=["POST"])
def score():
    data, err = _parse_body()
    if data is None:
        return err
    deck = data.get("deck")
    opponents = data.get("opponents")
    if not isinstance(deck, list) or not all(isinstance(x, str) for x in deck):
        return jsonify({"error": "deck must be a list of strings"}), 400
    if not isinstance(opponents, list):
        return jsonify({"error": "opponents must be a list"}), 400
    opp_decks: list[list[str]] = []
    for opp in opponents:
        if not isinstance(opp, list) or not all(isinstance(x, str) for x in opp):
            return jsonify({"error": "each opponent must be a list of strings"}), 400
        opp_decks.append(list(opp))
    model = _get_model()
    winrate = score_deck_vs_opponents(model, list(deck), opp_decks)
    return jsonify({"winrate": winrate})
