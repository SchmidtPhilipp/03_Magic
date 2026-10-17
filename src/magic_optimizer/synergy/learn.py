# src/magic_optimizer/synergy/learn.py
from __future__ import annotations

import json
from pathlib import Path

from magic_optimizer.synergy.graph import SynergyGraph


def learn_synergy_from_jsonl(path: str | Path) -> SynergyGraph:
    """Build synergy graph from match records (deck_a/deck_b/winrate_a)."""
    graph = SynergyGraph()
    target = Path(path)
    with target.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            deck_a = record.get("deck_a") or []
            deck_b = record.get("deck_b") or []
            if not isinstance(deck_a, list) or not isinstance(deck_b, list):
                continue
            try:
                wr_a = float(record.get("winrate_a", 0.5))
            except (TypeError, ValueError):
                wr_a = 0.5
            wr_a = max(0.0, min(1.0, wr_a))
            graph.add_deck([str(x) for x in deck_a], weight=wr_a)
            graph.add_deck([str(x) for x in deck_b], weight=1.0 - wr_a)
    return graph
