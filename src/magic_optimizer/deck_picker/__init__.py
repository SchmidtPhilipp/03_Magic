# src/magic_optimizer/deck_picker/__init__.py
from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.checkpoint import (
    DeckRLState,
    load_checkpoint,
    save_checkpoint,
    state_from_dict,
    state_to_dict,
    steps_to_dicts,
)
from magic_optimizer.deck_picker.complete import (
    complete_deck,
    complete_deck_with_trajectory,
    count_non_basics,
    fill_basics,
    refill_basics,
)
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy, NextCardPolicy
from magic_optimizer.deck_picker.mana import (
    estimate_deck_color_pips,
    pips_from_mana_cost,
    strip_basics,
)
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
    "DeckRLState",
    "DeckStep",
    "HeuristicNextCardPolicy",
    "NextCardPolicy",
    "ScoredCard",
    "SwapProposal",
    "apply_swap",
    "complete_deck",
    "complete_deck_with_trajectory",
    "count_non_basics",
    "estimate_deck_color_pips",
    "fill_basics",
    "legal_candidates",
    "load_checkpoint",
    "missing_cards",
    "pips_from_mana_cost",
    "pool_from_card_rows",
    "propose_swaps",
    "refill_basics",
    "save_checkpoint",
    "state_from_dict",
    "state_to_dict",
    "steps_to_dicts",
    "strip_basics",
    "union_pools",
]
