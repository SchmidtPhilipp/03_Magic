# src/magic_optimizer/league/job.py
from __future__ import annotations

import random
import uuid
from collections.abc import Callable
from typing import Any

from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.league.stop_policy import StopPolicy
from magic_optimizer.league.store import League
from magic_optimizer.league.types import JobState, LeagueDeck
from magic_optimizer.match_oracle.types import MatchOracle


class OptimizationJob:
    def __init__(
        self,
        league: League,
        oracle: MatchOracle,
        stop_policy: StopPolicy,
        *,
        games_per_match: int = 5,
        seed: int = 0,
        top_k: int = 5,
    ) -> None:
        self.league = league
        self.oracle = oracle
        self.stop_policy = stop_policy
        self.games_per_match = games_per_match
        self.rng = random.Random(seed)
        self.top_k = top_k
        self.state = JobState()
        # When set, challenge() prefers opponents with this provenance prefix.
        self.opponent_provenance_prefix: str | None = None

    def challenge(
        self,
        cards: list[str],
        *,
        deck_id: str | None = None,
        provenance: str = "challenger",
    ) -> dict[str, Any]:
        if len(self.league) == 0:
            raise ValueError("league is empty; bootstrap at least one deck")

        deck_id = deck_id or str(uuid.uuid4())
        try:
            challenger = self.league.get(deck_id)
        except KeyError:
            challenger = LeagueDeck(
                id=deck_id, cards=list(cards), provenance=provenance
            )
            self.league.add(challenger)

        opponent = self.league.sample_opponent(
            exclude_id=deck_id,
            rng=self.rng,
            provenance_prefix=getattr(self, "opponent_provenance_prefix", None),
        )
        deck_a = [CardRef(n) for n in challenger.cards]
        deck_b = [CardRef(n) for n in opponent.cards]
        result = self.oracle.play(deck_a, deck_b, games=self.games_per_match)

        winner_id: str | None = None
        loser_id: str | None = None
        if result.wins_a > result.wins_b:
            winner_id, loser_id = deck_id, opponent.id
            self.league.record_match(
                winner_id,
                loser_id,
                games=result.games_played,
                wins_winner=result.wins_a,
                wins_loser=result.wins_b,
            )
        elif result.wins_b > result.wins_a:
            winner_id, loser_id = opponent.id, deck_id
            self.league.record_match(
                winner_id,
                loser_id,
                games=result.games_played,
                wins_winner=result.wins_b,
                wins_loser=result.wins_a,
            )
        else:
            # Tie: still count games on both
            challenger.games += result.games_played
            opponent.games += result.games_played

        self.state.challenges += 1
        challenger = self.league.get(deck_id)
        self.state.best_deck_id = (
            self.league.top(1)[0].id if len(self.league) else deck_id
        )
        best = self.league.get(self.state.best_deck_id)
        self.state.best_winrate = best.winrate
        self.state.games_vs_top += result.games_played
        self.state.elo_history.append(challenger.elo)

        should_stop = self.stop_policy.should_stop(self.state)
        return {
            "challenger_id": deck_id,
            "opponent_id": opponent.id,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "result": {
                "wins_a": result.wins_a,
                "wins_b": result.wins_b,
                "games_played": result.games_played,
                "engine": result.engine,
            },
            "should_stop": should_stop,
            "job_state": {
                "best_deck_id": self.state.best_deck_id,
                "best_winrate": self.state.best_winrate,
                "games_vs_top": self.state.games_vs_top,
                "challenges": self.state.challenges,
            },
        }

    def run_until_stop(
        self,
        build_deck: Callable[[], list[str]],
        *,
        max_challenges: int = 50,
    ) -> JobState:
        for _ in range(max(0, max_challenges)):
            cards = build_deck()
            summary = self.challenge(cards)
            if summary["should_stop"]:
                break
        return self.state
