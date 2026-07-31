# src/magic_optimizer/dreamer/train.py
from __future__ import annotations

from pathlib import Path

from magic_optimizer.dreamer.replay import ReplayBuffer
from magic_optimizer.dreamer.world_model import WorldModel


def train_world_model_from_jsonl(
    path: str | Path,
    *,
    dim: int = 64,
    seed: int = 0,
    epochs: int = 200,
) -> WorldModel:
    buf = ReplayBuffer()
    buf.load_jsonl(path)
    model = WorldModel(dim=dim, seed=seed)
    model.fit(buf, epochs=epochs)
    return model
