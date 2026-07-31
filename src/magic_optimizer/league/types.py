# src/magic_optimizer/league/types.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LeagueDeck:
    id: str
    cards: list[str]
    elo: float = 1000.0
    wins: int = 0
    losses: int = 0
    games: int = 0
    provenance: str = "bootstrap"

    @property
    def winrate(self) -> float:
        if self.games <= 0:
            return 0.0
        # Approximate: wins are match wins; use wins/(wins+losses) if available
        decided = self.wins + self.losses
        if decided <= 0:
            return 0.0
        return self.wins / decided


@dataclass
class JobState:
    best_deck_id: str | None = None
    best_winrate: float = 0.0
    games_vs_top: int = 0
    elo_history: list[float] = field(default_factory=list)
    cancelled: bool = False
    challenges: int = 0
