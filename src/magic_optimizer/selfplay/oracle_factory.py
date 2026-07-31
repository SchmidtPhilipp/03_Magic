# src/magic_optimizer/selfplay/oracle_factory.py
from __future__ import annotations

from magic_optimizer.match_oracle.health import forge_available
from magic_optimizer.match_oracle.stub import StubMatchOracle
from magic_optimizer.match_oracle.types import MatchOracle


def make_oracle(*, backend: str = "stub", seed: int = 0) -> MatchOracle:
    """Create a MatchOracle. Forge is observe-only gated — never starts services."""
    if backend == "stub":
        return StubMatchOracle(seed=seed)
    if backend == "forge":
        if not forge_available():
            raise RuntimeError("forge unavailable")
        from magic_optimizer.match_oracle.forge import ForgeMatchOracle

        return ForgeMatchOracle()
    raise ValueError("backend must be 'stub' or 'forge'")
