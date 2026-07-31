# src/magic_optimizer/deck_picker/checkpoint.py
"""Persist and resume deck-level RL / optimization state (not in-game Forge)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints, DeckStep

CHECKPOINT_VERSION = 1


@dataclass
class DeckRLState:
    """Serializable state of the deck optimization / RL loop."""

    deck: list[CardRef]
    pool: dict[str, int]
    constraints: DeckConstraints
    ratings: dict[str, float] = field(default_factory=dict)
    iteration: int = 0
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def card_pool(self) -> CardPool:
        return CardPool(dict(self.pool))


def steps_to_dicts(steps: list[DeckStep]) -> list[dict[str, Any]]:
    return [
        {
            "action": s.action,
            "card": s.card.name,
            "score": s.score,
            "index": s.index,
            "alternatives": [
                {"name": a.card.name, "score": a.score} for a in s.alternatives
            ],
        }
        for s in steps
    ]


def _constraints_to_dict(c: DeckConstraints) -> dict[str, Any]:
    return {
        "deck_size": c.deck_size,
        "max_copies": c.max_copies,
        "banned": sorted(c.banned),
        "pinned": list(c.pinned),
        "non_basic_target": c.non_basic_target,
    }


def _constraints_from_dict(d: dict[str, Any]) -> DeckConstraints:
    return DeckConstraints(
        deck_size=int(d.get("deck_size", 60)),
        max_copies=int(d.get("max_copies", 4)),
        banned=frozenset(str(x) for x in (d.get("banned") or [])),
        pinned=tuple(str(x) for x in (d.get("pinned") or [])),
        non_basic_target=int(d.get("non_basic_target", 40)),
    )


def state_to_dict(state: DeckRLState) -> dict[str, Any]:
    return {
        "version": CHECKPOINT_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "iteration": int(state.iteration),
        "deck": [c.name for c in state.deck],
        "pool": {str(k): int(v) for k, v in state.pool.items()},
        "constraints": _constraints_to_dict(state.constraints),
        "ratings": {str(k): float(v) for k, v in state.ratings.items()},
        "trajectory": list(state.trajectory),
        "meta": dict(state.meta),
    }


def state_from_dict(data: dict[str, Any]) -> DeckRLState:
    version = int(data.get("version", 0))
    if version != CHECKPOINT_VERSION:
        raise ValueError(f"unsupported checkpoint version: {version}")
    deck_raw = data.get("deck") or []
    if not isinstance(deck_raw, list):
        raise ValueError("deck must be a list")
    pool_raw = data.get("pool") or {}
    if not isinstance(pool_raw, dict):
        raise ValueError("pool must be an object")
    return DeckRLState(
        deck=[CardRef(str(n)) for n in deck_raw],
        pool={str(k): int(v) for k, v in pool_raw.items()},
        constraints=_constraints_from_dict(data.get("constraints") or {}),
        ratings={str(k): float(v) for k, v in (data.get("ratings") or {}).items()},
        iteration=int(data.get("iteration", 0)),
        trajectory=list(data.get("trajectory") or []),
        meta=dict(data.get("meta") or {}),
    )


def save_checkpoint(path: str | Path, state: DeckRLState) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state_to_dict(state), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_checkpoint(path: str | Path) -> DeckRLState:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("checkpoint must be a JSON object")
    return state_from_dict(data)
