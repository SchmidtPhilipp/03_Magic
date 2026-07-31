"""Flask blueprint for collection management API."""

from __future__ import annotations

import os
import uuid
from io import BytesIO
from pathlib import Path

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file, session
from werkzeug.utils import secure_filename

import config
from magic_optimizer.collection.auth import current_username
from magic_optimizer.collection.repository import CollectionRepository
from magic_optimizer.vision.detect import detect_card_regions
from magic_optimizer.vision.overlay import render_overlay
from magic_optimizer.vision.scryfall import (
    attach_image_uri,
    enrich_detections_payload,
    lookup_card_name,
)

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


def _scan_dir() -> Path:
    base = Path(config.PATHS.get("upload_folder", "uploads")) / "scans"
    base.mkdir(parents=True, exist_ok=True)
    return base


@collection_bp.route("/api/<int:collection_id>/scan", methods=["POST"])
def api_scan_upload(collection_id: int):
    """Upload table photo, detect card regions, return overlay preview."""
    if not get_repo().get_collection(collection_id, _user_id()):
        return jsonify({"error": "collection not found"}), 404
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "empty file"}), 400

    session_uuid = uuid.uuid4().hex[:12]
    scan_folder = _scan_dir() / session_uuid
    scan_folder.mkdir(parents=True, exist_ok=True)
    ext = Path(secure_filename(file.filename)).suffix.lower() or ".jpg"
    original_path = scan_folder / f"original{ext}"
    overlay_path = scan_folder / "overlay.jpg"
    file.save(original_path)

    detections = detect_card_regions(str(original_path))
    scan_session = get_repo().create_scan_session(
        collection_id,
        _user_id(),
        str(original_path),
        detections,
    )
    if not scan_session:
        return jsonify({"error": "failed to create scan session"}), 500

    overlay_dets = enrich_detections_payload(scan_session.get("detections", []))
    render_overlay(str(original_path), overlay_dets, str(overlay_path))

    return jsonify(
        {
            "session_id": scan_session["id"],
            "detection_count": len(overlay_dets),
            "overlay_url": f"/collections/scans/{scan_session['id']}/overlay.jpg",
            "original_url": f"/collections/scans/{scan_session['id']}/original",
            "detections": overlay_dets,
        }
    )


@collection_bp.route("/scans/<int:session_id>/overlay.jpg")
def scan_overlay_image(session_id: int):
    session_row = get_repo().get_scan_session(session_id, _user_id())
    if not session_row:
        return jsonify({"error": "not found"}), 404
    overlay = Path(session_row["image_path"]).parent / "overlay.jpg"
    if not overlay.exists():
        render_overlay(
            session_row["image_path"],
            session_row.get("detections", []),
            str(overlay),
        )
    return send_file(overlay, mimetype="image/jpeg")


@collection_bp.route("/scans/<int:session_id>/original")
def scan_original_image(session_id: int):
    session_row = get_repo().get_scan_session(session_id, _user_id())
    if not session_row:
        return jsonify({"error": "not found"}), 404
    return send_file(session_row["image_path"])


@collection_bp.route("/api/scan/<int:session_id>", methods=["GET"])
def api_get_scan(session_id: int):
    session_row = get_repo().get_scan_session(session_id, _user_id())
    if not session_row:
        return jsonify({"error": "not found"}), 404
    detections = enrich_detections_payload(session_row.get("detections", []))
    session_row = {**session_row, "detections": detections}
    overlay_path = Path(session_row["image_path"]).parent / "overlay.jpg"
    if overlay_path.exists():
        render_overlay(
            session_row["image_path"],
            detections,
            str(overlay_path),
        )
    return jsonify(
        {
            **session_row,
            "overlay_url": f"/collections/scans/{session_id}/overlay.jpg",
            "original_url": f"/collections/scans/{session_id}/original",
        }
    )


@collection_bp.route("/api/scan/<int:session_id>/detections/<int:detection_id>", methods=["PATCH"])
def api_update_detection(session_id: int, detection_id: int):
    data = request.get_json(silent=True) or {}
    name = data.get("detected_name")
    meta = None
    if name:
        meta = lookup_card_name(name)
    det = get_repo().update_detection(
        detection_id,
        _user_id(),
        detected_name=meta["card_name"] if meta else name,
        set_code=meta.get("set_code") if meta else data.get("set_code"),
        collector_number=(
            meta.get("collector_number") if meta else data.get("collector_number")
        ),
        scryfall_id=meta.get("scryfall_id") if meta else data.get("scryfall_id"),
        status=data.get("status"),
    )
    if not det:
        return jsonify({"error": "not found"}), 404

    session_row = get_repo().get_scan_session(session_id, _user_id())
    if session_row:
        overlay_path = Path(session_row["image_path"]).parent / "overlay.jpg"
        dets = enrich_detections_payload(session_row.get("detections", []))
        render_overlay(
            session_row["image_path"],
            dets,
            str(overlay_path),
        )
    return jsonify(attach_image_uri(det))


@collection_bp.route("/api/scan/<int:session_id>/commit", methods=["POST"])
def api_commit_scan(session_id: int):
    added = get_repo().commit_scan_session(session_id, _user_id())
    if added == 0:
        session_row = get_repo().get_scan_session(session_id, _user_id())
        if not session_row:
            return jsonify({"error": "not found"}), 404
        return jsonify({"error": "no accepted cards to commit"}), 400
    return jsonify({"added": added})


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
