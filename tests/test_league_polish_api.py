# tests/test_league_polish_api.py
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


def _bootstrap(client):
    pool = {f"Card{i}": 4 for i in range(40)}
    ratings = {f"Card{i}": float(i) for i in range(40)}
    return client.post(
        "/api/league/bootstrap",
        json={"pool": pool, "ratings": ratings, "n": 2, "non_basic_target": 40},
    )


def test_progress_after_run(client):
    pool = {f"Card{i}": 4 for i in range(40)}
    ratings = {f"Card{i}": float(i) for i in range(40)}
    client.post(
        "/api/league/run",
        json={
            "pool": pool,
            "ratings": ratings,
            "n": 2,
            "max_challenges": 1,
            "games": 2,
            "stop": {"threshold": 0.0, "min_games": 0},
            "non_basic_target": 40,
        },
    )
    resp = client.get("/api/league/progress")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["challenges"] >= 1
    assert data["league_size"] >= 2
    assert "forge_available" in data


def test_trade_report_endpoint(client):
    resp = client.post(
        "/api/league/trade-report",
        json={"deck": ["Shock"] * 4, "owned": {"Shock": 1}},
    )
    assert resp.status_code == 200
    assert resp.get_json()["missing_total"] == 3


def test_export_arena(client):
    resp = client.post(
        "/api/league/export",
        json={"deck": ["Shock", "Shock", "Bolt"], "format": "arena"},
    )
    assert resp.status_code == 200
    assert "2 Shock" in resp.get_json()["text"]


def test_export_bad_format(client):
    resp = client.post(
        "/api/league/export",
        json={"deck": ["Shock"], "format": "pdf"},
    )
    assert resp.status_code == 400
