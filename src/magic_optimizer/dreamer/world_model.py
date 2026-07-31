# src/magic_optimizer/dreamer/world_model.py
from __future__ import annotations

from typing import Any

import numpy as np

from magic_optimizer.dreamer.encode import embed_deck
from magic_optimizer.dreamer.replay import ReplayBuffer


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 0:
        return vec
    return vec / norm


class WorldModel:
    def __init__(self, *, dim: int = 64, seed: int = 0) -> None:
        self.dim = dim
        self.seed = seed
        self._w = np.zeros(2 * dim, dtype=np.float64)
        self._b = 0.0
        self._trained = False

    def _features(self, deck_a: list[str], deck_b: list[str]) -> np.ndarray:
        ea = _l2_normalize(embed_deck(deck_a, dim=self.dim, seed=self.seed))
        eb = _l2_normalize(embed_deck(deck_b, dim=self.dim, seed=self.seed))
        return np.concatenate([ea, eb])

    def fit(
        self,
        buffer: ReplayBuffer,
        *,
        epochs: int = 200,
        lr: float = 0.05,
        ridge: float = 1e-2,
    ) -> dict[str, float]:
        del epochs, lr  # closed-form ridge; kept for API compatibility
        items = buffer.as_list()
        if not items:
            return {"loss": float("nan"), "n": 0.0}
        xs = np.stack(
            [self._features(list(t.deck_a), list(t.deck_b)) for t in items]
        )
        ys = np.array([t.winrate_a for t in items], dtype=np.float64)
        # Augment with bias column; closed-form ridge regression.
        ones = np.ones((xs.shape[0], 1), dtype=np.float64)
        xb = np.concatenate([xs, ones], axis=1)
        xtx = xb.T @ xb + ridge * np.eye(xb.shape[1])
        xty = xb.T @ ys
        theta = np.linalg.solve(xtx, xty)
        self._w = theta[:-1]
        self._b = float(theta[-1])
        self._trained = True
        pred = xs @ self._w + self._b
        loss = float(np.mean((pred - ys) ** 2))
        return {"loss": loss, "n": float(len(items))}

    def predict_winrate(self, deck_a: list[str], deck_b: list[str]) -> float:
        if not self._trained:
            return 0.5
        x = self._features(deck_a, deck_b)
        raw = float(x @ self._w + self._b)
        return float(min(1.0, max(0.0, raw)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dim": self.dim,
            "seed": self.seed,
            "w": self._w.tolist(),
            "b": self._b,
            "trained": self._trained,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldModel:
        model = cls(dim=int(data["dim"]), seed=int(data.get("seed", 0)))
        model._w = np.array(data["w"], dtype=np.float64)
        model._b = float(data["b"])
        model._trained = bool(data.get("trained", True))
        return model
