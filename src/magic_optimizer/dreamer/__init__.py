# src/magic_optimizer/dreamer/__init__.py
from magic_optimizer.dreamer.encode import embed_deck
from magic_optimizer.dreamer.imagine import rank_decks, score_deck_vs_opponents
from magic_optimizer.dreamer.policy import DreamerNextCardPolicy
from magic_optimizer.dreamer.replay import ReplayBuffer, Transition
from magic_optimizer.dreamer.world_model import WorldModel

__all__ = [
    "DreamerNextCardPolicy",
    "ReplayBuffer",
    "Transition",
    "WorldModel",
    "embed_deck",
    "rank_decks",
    "score_deck_vs_opponents",
]
