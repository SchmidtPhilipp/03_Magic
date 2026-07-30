# src/magic_optimizer/deck_picker/__init__.py
from magic_optimizer.deck_picker.candidates import legal_candidates
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
    "ScoredCard",
    "legal_candidates",
]
