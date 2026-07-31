# tests/test_dreamer_api.py
from __future__ import annotations

import pytest
from flask import Flask

from magic_optimizer.dreamer.api import dreamer_bp, reset_dreamer


@pytest.fixture
def client():
    reset_dreamer()
    app = Flask(__name__)
    app.register_blueprint(dreamer_bp)
    yield app.test_client()
    reset_dreamer()


def test_train_and_score(client):
    strong = ["Good"] * 60
    weak = ["Bad"] * 60
    records = [
        {"deck_a": strong, "deck_b": weak, "winrate_a": 0.9},
        {"deck_a": weak, "deck_b": strong, "winrate_a": 0.1},
    ] * 20
    resp = client.post("/api/dreamer/train", json={"records": records, "dim": 24})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["n"] == 40
    assert "loss" in data

    resp2 = client.post(
        "/api/dreamer/score",
        json={"deck": strong, "opponents": [weak]},
    )
    assert resp2.status_code == 200
    assert resp2.get_json()["winrate"] > 0.5


def test_score_without_train_returns_half(client):
    resp = client.post(
        "/api/dreamer/score",
        json={"deck": ["A"] * 60, "opponents": [["B"] * 60]},
    )
    assert resp.status_code == 200
    assert abs(resp.get_json()["winrate"] - 0.5) < 1e-9


def test_train_missing_records_400(client):
    resp = client.post("/api/dreamer/train", json={})
    assert resp.status_code == 400
