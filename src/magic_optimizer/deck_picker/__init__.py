# src/magic_optimizer/deck_picker/__init__.py
from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.complete import (
    complete_deck,
    complete_deck_with_trajectory,
    count_non_basics,
    fill_basics,
)
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy, NextCardPolicy
from magic_optimizer.deck_picker.missing import missing_cards
from magic_optimizer.deck_picker.modify import apply_swap, propose_swaps
from magic_optimizer.deck_picker.pools import pool_from_card_rows, union_pools
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
    DeckStep,
    ScoredCard,
    SwapProposal,
)

__all__ = [
    "BASIC_LANDS",
    "CardPool",
    "CardRef",
    "DeckConstraints",
    "DeckStep",
    "HeuristicNextCardPolicy",
    "NextCardPolicy",
    "ScoredCard",
    "SwapProposal",
    "apply_swap",
    "complete_deck",
    "complete_deck_with_trajectory",
    "count_non_basics",
    "fill_basics",
    "legal_candidates",
    "missing_cards",
    "pool_from_card_rows",
    "propose_swaps",
    "union_pools",
]
