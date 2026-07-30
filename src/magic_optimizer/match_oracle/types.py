from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from magic_optimizer.deck_picker.types import CardRef


@dataclass(frozen=True)
class MatchResult:
    wins_a: int
    wins_b: int
    games_played: int
    void_games: int = 0
    engine: str = ""
    details: str = ""

    @property
    def winrate_a(self) -> float:
        if self.games_played == 0:
            return 0.0
        return self.wins_a / self.games_played


class PlayerBackend(Protocol):
    name: str


class MatchOracle(Protocol):
    def play(
        self,
        deck_a: list[CardRef],
        deck_b: list[CardRef],
        *,
        games: int,
    ) -> MatchResult: ...


class ForgePlayerAI:
    name = "forge_ai"
