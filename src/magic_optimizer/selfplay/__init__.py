# src/magic_optimizer/selfplay/__init__.py
from magic_optimizer.selfplay.loop import SelfPlayLoop
from magic_optimizer.selfplay.oracle_factory import make_oracle

__all__ = ["SelfPlayLoop", "make_oracle"]
