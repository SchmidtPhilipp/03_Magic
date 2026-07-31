# tests/test_dreamer_encode.py
import numpy as np

from magic_optimizer.dreamer.encode import embed_deck


def test_embed_deterministic():
    a = embed_deck(["Shock", "Bolt"], dim=32, seed=1)
    b = embed_deck(["Bolt", "Shock"], dim=32, seed=1)
    assert a.shape == (32,)
    assert np.allclose(a, b)


def test_embed_counts_matter():
    one = embed_deck(["Shock"], dim=32, seed=0)
    two = embed_deck(["Shock", "Shock"], dim=32, seed=0)
    assert not np.allclose(one, two)


def test_embed_empty_zeros():
    z = embed_deck([], dim=16, seed=0)
    assert np.allclose(z, 0)
