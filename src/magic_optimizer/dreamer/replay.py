# src/magic_optimizer/dreamer/replay.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Transition:
    deck_a: tuple[str, ...]
    deck_b: tuple[str, ...]
    winrate_a: float


def _winrate_from_record(record: dict[str, Any]) -> float | None:
    if "winrate_a" in record:
        try:
            return float(record["winrate_a"])
        except (TypeError, ValueError):
            return None
    try:
        wins_a = int(record.get("wins_a", 0))
        games = int(record.get("games_played", 0))
    except (TypeError, ValueError):
        return None
    if games <= 0:
        return None
    return wins_a / games


class ReplayBuffer:
    def __init__(self) -> None:
        self._items: list[Transition] = []

    def add(self, transition: Transition) -> None:
        self._items.append(transition)

    def extend_from_records(self, records: list[dict]) -> int:
        added = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            deck_a = record.get("deck_a")
            deck_b = record.get("deck_b")
            if not isinstance(deck_a, list) or not isinstance(deck_b, list):
                continue
            wr = _winrate_from_record(record)
            if wr is None:
                continue
            self.add(
                Transition(
                    deck_a=tuple(str(x) for x in deck_a),
                    deck_b=tuple(str(x) for x in deck_b),
                    winrate_a=float(wr),
                )
            )
            added += 1
        return added

    def load_jsonl(self, path: str | Path) -> int:
        target = Path(path)
        records: list[dict] = []
        with target.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return self.extend_from_records(records)

    def __len__(self) -> int:
        return len(self._items)

    def as_list(self) -> list[Transition]:
        return list(self._items)
