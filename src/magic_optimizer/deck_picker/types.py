# src/magic_optimizer/deck_picker/types.py
from __future__ import annotations

from dataclasses import dataclass, field

BASIC_LANDS: frozenset[str] = frozenset(
    {"Plains", "Island", "Swamp", "Mountain", "Forest"}
)


@dataclass(frozen=True)
class CardRef:
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())


@dataclass(frozen=True)
class DeckConstraints:
    deck_size: int = 60
    max_copies: int = 4
    banned: frozenset[str] = field(default_factory=frozenset)
    pinned: tuple[str, ...] = ()
    non_basic_target: int = 40
    # Hard color limits (WUBRG letters). None = unrestricted.
    max_colors: int | None = None
    allowed_colors: frozenset[str] | None = None


@dataclass
class CardPool:
    available: dict[str, int]

    def copies_available(self, name: str) -> int:
        if name in BASIC_LANDS:
            return 10**9
        return int(self.available.get(name, 0))


@dataclass(frozen=True)
class ScoredCard:
    card: CardRef
    score: float


@dataclass(frozen=True)
class DeckStep:
    """One step in a deck-building trajectory."""

    action: str  # "pin" | "seed" | "add" | "fill_basics"
    card: CardRef
    score: float = 0.0
    alternatives: tuple[ScoredCard, ...] = ()
    index: int = 0  # deck size after this step


@dataclass(frozen=True)
class SwapProposal:
    """Suggest removing one card and adding another."""

    remove: CardRef
    add: CardRef
    score_delta: float
    remove_score: float
    add_score: float
