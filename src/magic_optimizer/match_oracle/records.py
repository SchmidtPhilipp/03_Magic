from __future__ import annotations

import json
from pathlib import Path

from magic_optimizer.match_oracle.types import MatchResult


def match_record_from_result(
    deck_a_names: list[str],
    deck_b_names: list[str],
    result: MatchResult,
) -> dict:
    return {
        "deck_a": deck_a_names,
        "deck_b": deck_b_names,
        "wins_a": result.wins_a,
        "wins_b": result.wins_b,
        "games_played": result.games_played,
        "void_games": result.void_games,
        "engine": result.engine,
        "winrate_a": result.winrate_a,
        "details": result.details,
    }


def append_match_record(path: str | Path, record: dict) -> None:
    target = Path(path)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
