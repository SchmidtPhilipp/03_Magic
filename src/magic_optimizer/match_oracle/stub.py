from __future__ import annotations

import hashlib

from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.types import MatchResult


def _sorted_names(deck: list[CardRef]) -> tuple[str, ...]:
    return tuple(sorted(card.name for card in deck))


def _game_winner_a(
    names_a: tuple[str, ...],
    names_b: tuple[str, ...],
    *,
    seed: int,
    game_index: int,
) -> bool:
    payload = f"{names_a}|{names_b}|{seed}|{game_index}".encode()
    bit = hashlib.sha256(payload).digest()[0] & 1
    return bit == 0


class StubMatchOracle:
    def __init__(self, *, seed: int = 0) -> None:
        self._seed = seed

    def play(
        self,
        deck_a: list[CardRef],
        deck_b: list[CardRef],
        *,
        games: int,
    ) -> MatchResult:
        if games < 1:
            raise ValueError("games must be at least 1")

        names_a = _sorted_names(deck_a)
        names_b = _sorted_names(deck_b)

        wins_a = 0
        wins_b = 0
        for i in range(games):
            if _game_winner_a(names_a, names_b, seed=self._seed, game_index=i):
                wins_a += 1
            else:
                wins_b += 1

        return MatchResult(
            wins_a=wins_a,
            wins_b=wins_b,
            games_played=games,
            void_games=0,
            engine="stub",
        )
