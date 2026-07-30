# tests/test_deck_picker_api.py
from __future__ import annotations

import pytest
from flask import Flask

from magic_optimizer.deck_picker.api import deck_picker_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(deck_picker_bp)
    return app.test_client()


def test_next_card_returns_scored_candidates(client):
    resp = client.post(
        "/api/deck-picker/next-card",
        json={
            "pool": {"Shock": 4, "Bolt": 2},
            "decklist": ["Shock"],
            "banned": ["Bolt"],
            "pinned": [],
            "ratings": {"Shock": 2.0, "Plains": 0.1},
            "k": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "candidates" in data
    names = [c["name"] for c in data["candidates"]]
    assert "Bolt" not in names
    assert "Shock" in names
    shock = next(c for c in data["candidates"] if c["name"] == "Shock")
    assert shock["score"] == 2.0


def test_next_card_missing_pool_returns_400(client):
    resp = client.post(
        "/api/deck-picker/next-card",
        json={"decklist": [], "k": 3},
    )
    assert resp.status_code == 400


def test_next_card_invalid_json_returns_400(client):
    resp = client.post(
        "/api/deck-picker/next-card",
        data="not json",
        content_type="text/plain",
    )
    assert resp.status_code == 400


def test_complete_returns_deck_and_empty_missing_without_owned(client):
    pool = {f"Card{i}": 4 for i in range(50)}
    ratings = {f"Card{i}": float(i) for i in range(50)}
    resp = client.post(
        "/api/deck-picker/complete",
        json={
            "pool": pool,
            "decklist": [],
            "banned": [],
            "pinned": ["Card49"],
            "ratings": ratings,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["deck"]) == 60
    assert data["missing"] == []
    assert "Card49" in data["deck"]


def test_complete_missing_pool_returns_400(client):
    resp = client.post("/api/deck-picker/complete", json={"ratings": {}})
    assert resp.status_code == 400


def test_complete_reports_missing_vs_owned(client):
    pool = {f"Card{i}": 4 for i in range(50)}
    ratings = {f"Card{i}": float(i) for i in range(50)}
    resp = client.post(
        "/api/deck-picker/complete",
        json={
            "pool": pool,
            "decklist": [],
            "banned": [],
            "pinned": ["Card49"],
            "ratings": ratings,
            "owned": {"Card49": 0, "Card0": 1},
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    missing = {name: qty for name, qty in data["missing"]}
    assert missing.get("Card49", 0) >= 1


@pytest.mark.parametrize(
    "body,content_type",
    [
        ("[]", "application/json"),
        ('"hello"', "application/json"),
    ],
)
def test_non_object_json_body_returns_400(client, body, content_type):
    resp = client.post(
        "/api/deck-picker/next-card",
        data=body,
        content_type=content_type,
    )
    assert resp.status_code == 400
    assert "object" in resp.get_json()["error"].lower()


def test_pool_non_int_value_returns_400(client):
    resp = client.post(
        "/api/deck-picker/next-card",
        json={
            "pool": {"Shock": "four"},
            "decklist": [],
            "ratings": {},
        },
    )
    assert resp.status_code == 400
    assert "integer" in resp.get_json()["error"].lower()


def test_decklist_string_returns_400(client):
    resp = client.post(
        "/api/deck-picker/next-card",
        json={
            "pool": {"Shock": 4},
            "decklist": "Shock",
            "ratings": {},
        },
    )
    assert resp.status_code == 400
    assert "list" in resp.get_json()["error"].lower()
