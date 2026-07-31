# tests/test_selfplay_oracle_factory.py
import pytest

from magic_optimizer.match_oracle.stub import StubMatchOracle
from magic_optimizer.selfplay.oracle_factory import make_oracle


def test_make_stub():
    oracle = make_oracle(backend="stub", seed=1)
    assert isinstance(oracle, StubMatchOracle)


def test_make_forge_unavailable_raises(monkeypatch):
    monkeypatch.setattr(
        "magic_optimizer.selfplay.oracle_factory.forge_available",
        lambda: False,
    )
    with pytest.raises(RuntimeError, match="forge unavailable"):
        make_oracle(backend="forge")


def test_unknown_backend():
    with pytest.raises(ValueError):
        make_oracle(backend="xmage")
