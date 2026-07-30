from __future__ import annotations

import pytest
from flask import Flask

from magic_optimizer.match_oracle.api import match_oracle_bp
from magic_optimizer.match_oracle.types import MatchResult


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(match_oracle_bp)
    return app.test_client()


def test_health_returns_forge_available(client, monkeypatch):
    monkeypatch.setattr(
        "magic_optimizer.match_oracle.api.forge_available",
        lambda **kwargs: True,
    )
    resp = client.get("/api/match-oracle/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"forge_available": True}


def test_health_forge_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        "magic_optimizer.match_oracle.api.forge_available",
        lambda **kwargs: False,
    )
    resp = client.get("/api/match-oracle/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"forge_available": False}


def test_play_stub_default_backend(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": ["Shock"] * 60,
            "deck_b": ["Bolt"] * 60,
            "games": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["games_played"] == 5
    assert data["wins_a"] + data["wins_b"] == 5
    assert data["engine"] == "stub"
    assert data["void_games"] == 0
    assert data["winrate_a"] == data["wins_a"] / 5
    assert "details" in data


def test_play_stub_explicit_backend(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": ["Shock"],
            "deck_b": ["Bolt"],
            "games": 3,
            "backend": "stub",
        },
    )
    assert resp.status_code == 200
    assert resp.get_json()["engine"] == "stub"


def test_play_stub_is_deterministic(client):
    body = {
        "deck_a": ["Shock"] * 60,
        "deck_b": ["Bolt"] * 60,
        "games": 7,
        "backend": "stub",
    }
    r1 = client.post("/api/match-oracle/play", json=body).get_json()
    r2 = client.post("/api/match-oracle/play", json=body).get_json()
    assert r1 == r2


def test_play_missing_deck_a_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={"deck_b": ["Bolt"], "games": 1},
    )
    assert resp.status_code == 400


def test_play_missing_deck_b_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={"deck_a": ["Shock"], "games": 1},
    )
    assert resp.status_code == 400


def test_play_games_zero_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={"deck_a": ["Shock"], "deck_b": ["Bolt"], "games": 0},
    )
    assert resp.status_code == 400


def test_play_games_exceeds_max_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={"deck_a": ["Shock"], "deck_b": ["Bolt"], "games": 101},
    )
    assert resp.status_code == 400
    assert "at most 100" in resp.get_json()["error"]


def test_play_games_missing_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={"deck_a": ["Shock"], "deck_b": ["Bolt"]},
    )
    assert resp.status_code == 400


def test_play_invalid_json_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        data="not json",
        content_type="text/plain",
    )
    assert resp.status_code == 400


def test_play_non_object_json_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        data="[]",
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_play_deck_not_list_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": "Shock",
            "deck_b": ["Bolt"],
            "games": 1,
        },
    )
    assert resp.status_code == 400


def test_play_deck_entry_not_string_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": ["Shock", 1],
            "deck_b": ["Bolt"],
            "games": 1,
        },
    )
    assert resp.status_code == 400


def test_play_invalid_backend_returns_400(client):
    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": ["Shock"],
            "deck_b": ["Bolt"],
            "games": 1,
            "backend": "dreamer",
        },
    )
    assert resp.status_code == 400


def test_play_forge_unavailable_returns_503(client, monkeypatch):
    monkeypatch.setattr(
        "magic_optimizer.match_oracle.api.forge_available",
        lambda **kwargs: False,
    )
    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": ["Shock"],
            "deck_b": ["Bolt"],
            "games": 1,
            "backend": "forge",
        },
    )
    assert resp.status_code == 503


def test_play_forge_available_returns_result(client, monkeypatch):
    monkeypatch.setattr(
        "magic_optimizer.match_oracle.api.forge_available",
        lambda **kwargs: True,
    )

    class FakeForgeOracle:
        def play(self, deck_a, deck_b, *, games):
            del deck_a, deck_b
            return MatchResult(
                wins_a=2,
                wins_b=1,
                games_played=games,
                void_games=0,
                engine="forge",
                details="ok",
            )

    monkeypatch.setattr(
        "magic_optimizer.match_oracle.api.ForgeMatchOracle",
        FakeForgeOracle,
    )

    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": ["Shock"],
            "deck_b": ["Bolt"],
            "games": 3,
            "backend": "forge",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {
        "wins_a": 2,
        "wins_b": 1,
        "games_played": 3,
        "void_games": 0,
        "engine": "forge",
        "winrate_a": 2 / 3,
        "details": "ok",
    }


def test_play_forge_config_error_returns_503(client, monkeypatch):
    monkeypatch.setattr(
        "magic_optimizer.match_oracle.api.forge_available",
        lambda **kwargs: True,
    )

    def raise_config_error(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("invalid FORGE_TIMEOUT_SEC: 'bad'")

    monkeypatch.setattr(
        "magic_optimizer.match_oracle.api.ForgeMatchOracle",
        raise_config_error,
    )

    resp = client.post(
        "/api/match-oracle/play",
        json={
            "deck_a": ["Shock"],
            "deck_b": ["Bolt"],
            "games": 1,
            "backend": "forge",
        },
    )
    assert resp.status_code == 503
    assert "FORGE_TIMEOUT_SEC" in resp.get_json()["error"]
