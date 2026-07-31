# tests/test_league_store.py
import json
from pathlib import Path

from magic_optimizer.league.store import League
from magic_optimizer.league.types import LeagueDeck


def test_add_top_and_record_match():
    league = League()
    a = LeagueDeck(id="a", cards=["Shock"] * 60, elo=1000)
    b = LeagueDeck(id="b", cards=["Bolt"] * 60, elo=1000)
    league.add(a)
    league.add(b)
    league.record_match("a", "b", games=5, wins_winner=3, wins_loser=2)
    assert league.get("a").elo > 1000
    assert league.get("b").elo < 1000
    assert league.get("a").wins == 1
    assert league.get("a").games == 5
    assert league.top(1)[0].id == "a"


def test_json_roundtrip(tmp_path: Path):
    league = League()
    league.add(LeagueDeck(id="x", cards=["A", "B"], elo=1100, wins=2, losses=1, games=10))
    path = tmp_path / "league.json"
    league.save_json(path)
    loaded = League.load_json(path)
    assert loaded.get("x").elo == 1100
    assert loaded.get("x").cards == ["A", "B"]
    assert json.loads(path.read_text())["decks"][0]["id"] == "x"


def test_sample_opponent_excludes_self():
    import random

    league = League()
    league.add(LeagueDeck(id="a", cards=["A"]))
    league.add(LeagueDeck(id="b", cards=["B"]))
    opp = league.sample_opponent(exclude_id="a", rng=random.Random(0))
    assert opp.id == "b"
