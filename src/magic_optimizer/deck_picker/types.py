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
