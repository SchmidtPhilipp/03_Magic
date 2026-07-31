# tests/test_league_api.py
from __future__ import annotations

import pytest
from flask import Flask

from magic_optimizer.league.api import league_bp, reset_league


@pytest.fixture
def client():
    reset_league()
    app = Flask(__name__)
    app.register_blueprint(league_bp)
    yield app.test_client()
    reset_league()


def _pool_payload(n: int = 40) -> dict:
    return {
        "pool": {f"Card{i}": 4 for i in range(n)},
        "ratings": {f"Card{i}": float(i) for i in range(n)},
        "n": 2,
        "deck_size": 60,
        "non_basic_target": 40,
    }


def test_bootstrap_creates_league(client):
    resp = client.post("/api/league/bootstrap", json=_pool_payload())
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["size"] == 2
    assert len(data["deck_ids"]) == 2


def test_standings_after_bootstrap(client):
    client.post("/api/league/bootstrap", json=_pool_payload())
    resp = client.get("/api/league/standings")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["standings"]) == 2
    assert "elo" in data["standings"][0]


def test_challenge_empty_league_400(client):
    resp = client.post(
        "/api/league/challenge",
        json={"deck": ["Shock"] * 60},
    )
    assert resp.status_code == 400


def test_challenge_updates_standings(client):
    client.post("/api/league/bootstrap", json=_pool_payload())
    resp = client.post(
        "/api/league/challenge",
        json={"deck": [f"Card{i % 40}" for i in range(60)], "games": 3, "backend": "stub"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "winner_id" in data or data.get("result")
    assert "should_stop" in data


def test_run_returns_job_state(client):
    payload = _pool_payload()
    payload["n"] = 2
    payload["max_challenges"] = 2
    payload["stop"] = {"threshold": 0.0, "min_games": 0}
    payload["games"] = 3
    resp = client.post("/api/league/run", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "job_state" in data
    assert "standings" in data
    assert data["job_state"]["challenges"] >= 1


def test_reset_query_clears_league(client):
    client.post("/api/league/bootstrap", json=_pool_payload())
    resp = client.get("/api/league/standings?reset=1")
    assert resp.status_code == 200
    assert resp.get_json()["standings"] == []
