from __future__ import annotations

import json
from pathlib import Path

from magic_optimizer.match_oracle.records import (
    append_match_record,
    match_record_from_result,
)
from magic_optimizer.match_oracle.types import MatchResult


def test_match_record_from_result():
    result = MatchResult(
        wins_a=3,
        wins_b=1,
        games_played=4,
        void_games=0,
        engine="forge",
        details="ok",
    )
    record = match_record_from_result(
        ["Shock", "Mountain"],
        ["Bolt", "Island"],
        result,
    )
    assert record == {
        "deck_a": ["Shock", "Mountain"],
        "deck_b": ["Bolt", "Island"],
        "wins_a": 3,
        "wins_b": 1,
        "games_played": 4,
        "void_games": 0,
        "engine": "forge",
        "winrate_a": 0.75,
        "details": "ok",
    }


def test_append_match_record_round_trip(tmp_path: Path):
    path = tmp_path / "matches.jsonl"
    record = {
        "deck_a": ["Shock"],
        "deck_b": ["Bolt"],
        "wins_a": 2,
        "wins_b": 1,
        "games_played": 3,
        "void_games": 0,
        "engine": "stub",
        "winrate_a": 2 / 3,
        "details": "",
    }
    append_match_record(path, record)
    append_match_record(path, {**record, "wins_a": 1})

    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == record
    assert json.loads(lines[1])["wins_a"] == 1
