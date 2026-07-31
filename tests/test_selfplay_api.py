# tests/test_selfplay_api.py
from __future__ import annotations

import pytest
from flask import Flask

from magic_optimizer.selfplay.api import reset_selfplay, selfplay_bp


@pytest.fixture
def client():
    reset_selfplay()
    app = Flask(__name__)
    app.register_blueprint(selfplay_bp)
    yield app.test_client()
    reset_selfplay()


def test_selfplay_run(client):
    pool = {f"Card{i}": 4 for i in range(40)}
    ratings = {f"Card{i}": float(i) for i in range(40)}
    resp = client.post(
        "/api/selfplay/run",
        json={
            "pool": pool,
            "ratings": ratings,
            "bootstrap_n": 2,
            "max_challenges": 2,
            "games": 2,
            "backend": "stub",
            "stop": {"threshold": 0.0, "min_games": 0},
            "non_basic_target": 40,
            "retrain_every": 1,
            "dim": 16,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["model_trained"] is True
    assert data["job_state"]["challenges"] >= 1


def test_selfplay_forge_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        "magic_optimizer.selfplay.oracle_factory.forge_available",
        lambda: False,
    )
    resp = client.post(
        "/api/selfplay/run",
        json={
            "pool": {"A": 4},
            "ratings": {"A": 1.0},
            "backend": "forge",
            "bootstrap_n": 1,
            "max_challenges": 1,
        },
    )
    assert resp.status_code == 503
    assert "forge unavailable" in resp.get_json()["error"]
