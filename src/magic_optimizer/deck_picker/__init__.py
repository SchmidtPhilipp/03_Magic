# src/magic_optimizer/deck_picker/__init__.py
from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.complete import (
    complete_deck,
    count_non_basics,
    fill_basics,
)
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy, NextCardPolicy
from magic_optimizer.deck_picker.missing import missing_cards
from magic_optimizer.deck_picker.pools import pool_from_card_rows, union_pools
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
    ScoredCard,
)

__all__ = [
    "BASIC_LANDS",
    "CardPool",
    "CardRef",
    "DeckConstraints",
    "HeuristicNextCardPolicy",
    "NextCardPolicy",
    "ScoredCard",
    "complete_deck",
    "count_non_basics",
    "fill_basics",
    "legal_candidates",
    "missing_cards",
    "pool_from_card_rows",
    "union_pools",
]
