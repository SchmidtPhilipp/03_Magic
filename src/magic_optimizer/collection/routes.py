"""Flask blueprint for collection management API."""

from __future__ import annotations

import os
from io import BytesIO

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, session

import config
from magic_optimizer.collection.auth import current_username
from magic_optimizer.collection.repository import CollectionRepository

collection_bp = Blueprint(
    "collection",
    __name__,
    url_prefix="/collections",
)

_repo: CollectionRepository | None = None


def get_repo() -> CollectionRepository:
    global _repo
    if _repo is None:
        _repo = CollectionRepository()
    return _repo


def _user_id() -> int:
    username = current_username()
    return get_repo().ensure_user(username)


@collection_bp.route("/")
def collections_page():
    """Collection manager UI."""
    return render_template("collections.html", config=config)


@collection_bp.route("/api", methods=["GET"])
def api_list_collections():
    user_id = _user_id()
    items = get_repo().list_collections(user_id)
    return jsonify({"collections": items, "user": current_username()})


@collection_bp.route("/api", methods=["POST"])
def api_create_collection():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    description = (data.get("description") or "").strip()
    coll = get_repo().create_collection(_user_id(), name, description)
    return jsonify(coll), 201


@collection_bp.route("/api/<int:collection_id>", methods=["GET"])
def api_get_collection(collection_id: int):
    coll = get_repo().get_collection(collection_id, _user_id())
    if not coll:
        return jsonify({"error": "not found"}), 404
    sets = get_repo().distinct_sets(collection_id, _user_id())
    cards = get_repo().list_cards(collection_id, _user_id())
    return jsonify({"collection": coll, "sets": sets, "cards": cards})


@collection_bp.route("/api/<int:collection_id>", methods=["DELETE"])
def api_delete_collection(collection_id: int):
    if not get_repo().delete_collection(collection_id, _user_id()):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@collection_bp.route("/api/<int:collection_id>/cards", methods=["POST"])
def api_add_card(collection_id: int):
    data = request.get_json(silent=True) or {}
    name = (data.get("card_name") or data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "card_name required"}), 400
    card = get_repo().add_card(
        collection_id,
        _user_id(),
        card_name=name,
        amount=int(data.get("amount") or 1),
        set_code=data.get("set_code"),
        collector_number=data.get("collector_number"),
        scryfall_id=data.get("scryfall_id"),
        source=data.get("source") or "manual",
    )
    if not card:
        return jsonify({"error": "collection not found"}), 404
    return jsonify(card), 201


@collection_bp.route(
    "/api/<int:collection_id>/cards/<int:card_id>", methods=["DELETE"]
)
def api_remove_card(collection_id: int, card_id: int):
    if not get_repo().remove_card(card_id, collection_id, _user_id()):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@collection_bp.route("/api/<int:collection_id>/import", methods=["POST"])
def api_import_csv(collection_id: int):
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "empty file"}), 400
    try:
        df = pd.read_csv(BytesIO(file.read()))
        count = get_repo().import_csv(collection_id, _user_id(), df)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"imported": count})


@collection_bp.route("/api/<int:collection_id>/use-for-optimize", methods=["POST"])
def api_use_for_optimize(collection_id: int):
    """Store collection selection in session for the optimizer page."""
    data = request.get_json(silent=True) or {}
    set_codes = data.get("set_codes") or None
    card_ids = data.get("card_ids") or None
    coll = get_repo().get_collection(collection_id, _user_id())
    if not coll:
        return jsonify({"error": "not found"}), 404
    df = get_repo().to_optimizer_dataframe(
        collection_id, _user_id(), set_codes=set_codes, card_ids=card_ids
    )
    if df.empty:
        return jsonify({"error": "no cards in selection"}), 400
    upload_dir = config.PATHS.get("upload_folder", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"collection_{collection_id}.csv"
    filepath = os.path.join(upload_dir, filename)
    df.to_csv(filepath, index=False)
    session["uploaded_file"] = filename
    session["collection_id"] = collection_id
    session["collection_name"] = coll["name"]
    return jsonify(
        {
            "ok": True,
            "filename": filename,
            "card_count": len(df),
            "collection_name": coll["name"],
        }
    )
