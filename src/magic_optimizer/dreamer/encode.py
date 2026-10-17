# src/magic_optimizer/dreamer/encode.py
from __future__ import annotations

import hashlib

import numpy as np

# Cache deterministic card vectors — WorldModel.fit re-embeds the full replay
# often; RandomState construction per call was the hot path.
_CARD_VEC_CACHE: dict[tuple[int, int, str], np.ndarray] = {}


def _card_vector(name: str, *, dim: int, seed: int) -> np.ndarray:
    key = (seed, dim, name)
    hit = _CARD_VEC_CACHE.get(key)
    if hit is not None:
        return hit
    digest = hashlib.sha256(f"{seed}:{name}".encode("utf-8")).digest()
    seed_i = int.from_bytes(digest[:8], "little") % (2**32 - 1)
    rng = np.random.RandomState(seed_i)
    vec = rng.normal(size=dim).astype(np.float64)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    _CARD_VEC_CACHE[key] = vec
    return vec


def embed_deck(names: list[str], *, dim: int = 64, seed: int = 0) -> np.ndarray:
    """Deterministic, order-insensitive multiset embedding of card names."""
    if dim < 1:
        raise ValueError("dim must be >= 1")
    acc = np.zeros(dim, dtype=np.float64)
    if not names:
        return acc
    for name in names:
        acc += _card_vector(str(name), dim=dim, seed=seed)
    # Keep magnitude so copy counts remain distinguishable after summing.
    return acc
