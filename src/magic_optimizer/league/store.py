# src/magic_optimizer/league/store.py
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from magic_optimizer.league.elo import update_elo
from magic_optimizer.league.types import LeagueDeck


class League:
    def __init__(self) -> None:
        self._decks: dict[str, LeagueDeck] = {}

    def add(self, deck: LeagueDeck) -> None:
        self._decks[deck.id] = deck

    def get(self, deck_id: str) -> LeagueDeck:
        return self._decks[deck_id]

    def __len__(self) -> int:
        return len(self._decks)

    def all(self) -> list[LeagueDeck]:
        return list(self._decks.values())

    def top(self, k: int) -> list[LeagueDeck]:
        return sorted(self._decks.values(), key=lambda d: (-d.elo, d.id))[: max(0, k)]

    def sample_opponent(
        self,
        *,
        exclude_id: str | None = None,
        rng: random.Random | None = None,
    ) -> LeagueDeck:
        rng = rng or random.Random()
        candidates = [d for d in self._decks.values() if d.id != exclude_id]
        if not candidates:
            raise ValueError("no opponent available")
        ranked = sorted(candidates, key=lambda d: (-d.elo, d.id))
        pool = ranked[: max(1, len(ranked) // 2)] if len(ranked) >= 2 else ranked
        return rng.choice(pool)

    def record_match(
        self,
        winner_id: str,
        loser_id: str,
        *,
        games: int,
        wins_winner: int,
        wins_loser: int,
        k: float = 32.0,
    ) -> None:
        winner = self._decks[winner_id]
        loser = self._decks[loser_id]
        new_w, new_l = update_elo(winner.elo, loser.elo, 1.0, k=k)
        winner.elo = new_w
        loser.elo = new_l
        winner.wins += 1
        loser.losses += 1
        winner.games += games
        loser.games += games

    def to_dict(self) -> dict[str, Any]:
        return {
            "decks": [
                {
                    "id": d.id,
                    "cards": list(d.cards),
                    "elo": d.elo,
                    "wins": d.wins,
                    "losses": d.losses,
                    "games": d.games,
                    "provenance": d.provenance,
                }
                for d in self._decks.values()
            ]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> League:
        league = cls()
        for raw in data.get("decks") or []:
            league.add(
                LeagueDeck(
                    id=str(raw["id"]),
                    cards=list(raw.get("cards") or []),
                    elo=float(raw.get("elo", 1000)),
                    wins=int(raw.get("wins", 0)),
                    losses=int(raw.get("losses", 0)),
                    games=int(raw.get("games", 0)),
                    provenance=str(raw.get("provenance", "bootstrap")),
                )
            )
        return league

    def save_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> League:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
