"""Tests for scan session persistence."""

import tempfile
from pathlib import Path

import pytest

from magic_optimizer.collection.repository import CollectionRepository


@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as tmp:
        yield CollectionRepository(str(Path(tmp) / "test.db"))


def test_scan_session_create_and_commit(repo):
    user_id = repo.ensure_user("philipp")
    coll = repo.create_collection(user_id, "Scan Test")
    cid = coll["id"]

    session = repo.create_scan_session(
        cid,
        user_id,
        "/tmp/scan.jpg",
        [
            {
                "bbox_x": 0.1,
                "bbox_y": 0.1,
                "bbox_w": 0.2,
                "bbox_h": 0.3,
                "detected_name": "Forest",
                "set_code": "FIN",
                "status": "accepted",
            },
            {
                "bbox_x": 0.5,
                "bbox_y": 0.1,
                "bbox_w": 0.2,
                "bbox_h": 0.3,
                "detected_name": "Unbekannt",
                "status": "rejected",
            },
        ],
    )
    assert session is not None
    assert len(session["detections"]) == 2

    added = repo.commit_scan_session(session["id"], user_id)
    assert added == 1
    cards = repo.list_cards(cid, user_id)
    assert len(cards) == 1
    assert cards[0]["card_name"] == "Forest"
