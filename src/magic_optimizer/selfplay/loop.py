# src/magic_optimizer/selfplay/loop.py
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.dreamer.policy import DreamerNextCardPolicy
from magic_optimizer.dreamer.replay import ReplayBuffer, Transition
from magic_optimizer.dreamer.world_model import WorldModel
from magic_optimizer.league.bootstrap import deck_from_policy, seed_league_from_pool
from magic_optimizer.league.job import OptimizationJob
from magic_optimizer.league.stop_policy import StopPolicy
from magic_optimizer.league.store import League
from magic_optimizer.match_oracle.records import append_match_record
from magic_optimizer.match_oracle.types import MatchOracle


class SelfPlayLoop:
    def __init__(
        self,
        *,
        oracle: MatchOracle,
        stop_policy: StopPolicy,
        pool: CardPool,
        constraints: DeckConstraints,
        ratings: dict[str, float],
        records_path: str | Path | None = None,
        games_per_match: int = 5,
        seed: int = 0,
        retrain_every: int = 2,
        dim: int = 64,
    ) -> None:
        self.oracle = oracle
        self.stop_policy = stop_policy
        self.pool = pool
        self.constraints = constraints
        self.ratings = dict(ratings)
        self.records_path = Path(records_path) if records_path else None
        self.games_per_match = games_per_match
        self.seed = seed
        self.retrain_every = max(1, retrain_every)
        self.dim = dim
        self.rng = random.Random(seed)
        self.league = League()
        self.buffer = ReplayBuffer()
        self.model = WorldModel(dim=dim, seed=seed)
        self._model_trained = False

    def _build_challenger(self) -> list[str]:
        if self._model_trained and len(self.league) > 0:
            opponents = [list(d.cards) for d in self.league.top(min(5, len(self.league)))]
            policy: HeuristicNextCardPolicy | DreamerNextCardPolicy = DreamerNextCardPolicy(
                self.model,
                opponents,
                fallback_ratings=self.ratings,
            )
        else:
            jittered = {
                name: score + self.rng.uniform(-1.0, 1.0)
                for name, score in self.ratings.items()
            }
            policy = HeuristicNextCardPolicy(jittered)
        return deck_from_policy(policy, self.pool, self.constraints)

    def _record_from_summary(self, summary: dict[str, Any]) -> None:
        challenger = self.league.get(summary["challenger_id"])
        opponent = self.league.get(summary["opponent_id"])
        result = summary["result"]
        games = int(result.get("games_played", 0))
        wins_a = int(result.get("wins_a", 0))
        winrate_a = (wins_a / games) if games > 0 else 0.5
        self.buffer.add(
            Transition(
                deck_a=tuple(challenger.cards),
                deck_b=tuple(opponent.cards),
                winrate_a=winrate_a,
            )
        )
        if self.records_path is not None:
            self.records_path.parent.mkdir(parents=True, exist_ok=True)
            append_match_record(
                self.records_path,
                {
                    "deck_a": list(challenger.cards),
                    "deck_b": list(opponent.cards),
                    "wins_a": wins_a,
                    "wins_b": int(result.get("wins_b", 0)),
                    "games_played": games,
                    "winrate_a": winrate_a,
                    "engine": result.get("engine", ""),
                    "challenger_id": summary["challenger_id"],
                    "opponent_id": summary["opponent_id"],
                },
            )

    def run(
        self,
        *,
        bootstrap_n: int = 3,
        max_challenges: int = 20,
    ) -> dict[str, Any]:
        seed_league_from_pool(
            self.league,
            HeuristicNextCardPolicy(self.ratings),
            self.pool,
            self.constraints,
            n=bootstrap_n,
            rng=random.Random(self.seed),
        )
        job = OptimizationJob(
            self.league,
            self.oracle,
            self.stop_policy,
            games_per_match=self.games_per_match,
            seed=self.seed,
        )
        records_written = 0
        for _ in range(max(0, max_challenges)):
            cards = self._build_challenger()
            summary = job.challenge(cards, provenance="selfplay")
            self._record_from_summary(summary)
            records_written += 1
            if job.state.challenges % self.retrain_every == 0 and len(self.buffer) > 0:
                self.model.fit(self.buffer)
                self._model_trained = True
            if summary["should_stop"]:
                break

        standings = [
            {
                "id": d.id,
                "elo": d.elo,
                "winrate": d.winrate,
                "wins": d.wins,
                "losses": d.losses,
                "games": d.games,
            }
            for d in self.league.top(50)
        ]
        return {
            "job_state": {
                "best_deck_id": job.state.best_deck_id,
                "best_winrate": job.state.best_winrate,
                "games_vs_top": job.state.games_vs_top,
                "challenges": job.state.challenges,
            },
            "standings": standings,
            "league_size": len(self.league),
            "model_trained": self._model_trained,
            "records_written": records_written,
            "replay_size": len(self.buffer),
        }
