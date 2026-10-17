# src/magic_optimizer/selfplay/loop.py
from __future__ import annotations

import random
from collections.abc import Callable
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
from magic_optimizer.meta.sealed_sim import default_ratings_for_pool
from magic_optimizer.synergy.graph import SynergyGraph

OPPONENT_PROVENANCE = "opponent_sealed"


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
        synergy: SynergyGraph | None = None,
        synergy_scale: float = 0.1,
        card_info: Callable[[str], dict | None] | None = None,
        color_pips: dict[str, int] | None = None,
        opponent_pool_factory: Callable[[int], CardPool] | None = None,
        opponent_refresh_games: int = 100,
        opponent_bootstrap_n: int | None = None,
    ) -> None:
        self.oracle = oracle
        self.stop_policy = stop_policy
        # Fixed hero pool (never regenerated).
        self.pool = pool
        self.constraints = constraints
        self.ratings = dict(ratings)
        self.records_path = Path(records_path) if records_path else None
        self.games_per_match = games_per_match
        self.seed = seed
        self.retrain_every = max(1, retrain_every)
        self.dim = dim
        self.synergy = synergy
        self.synergy_scale = float(synergy_scale)
        self.card_info = card_info
        self.color_pips = color_pips
        self.rng = random.Random(seed)
        self.league = League()
        self.buffer = ReplayBuffer()
        self.model = WorldModel(dim=dim, seed=seed)
        self._model_trained = False
        self.opponent_pool_factory = opponent_pool_factory
        self.opponent_refresh_games = max(1, int(opponent_refresh_games))
        self.opponent_bootstrap_n = opponent_bootstrap_n
        self._games_since_refresh = 0
        self._opponent_epoch = 0
        self._opponent_refresh_count = 0
        self._last_opponent_pool_size = 0

    def _heuristic(self, ratings: dict[str, float]) -> HeuristicNextCardPolicy:
        return HeuristicNextCardPolicy(
            ratings,
            synergy=self.synergy,
            synergy_scale=self.synergy_scale,
        )

    def _opponent_decks(self) -> list:
        return [
            d
            for d in self.league.all()
            if d.provenance.startswith(OPPONENT_PROVENANCE)
        ]

    def _build_challenger(self) -> list[str]:
        opp_decks = self._opponent_decks()
        if self._model_trained and opp_decks:
            opponents = [list(d.cards) for d in sorted(opp_decks, key=lambda d: -d.elo)[:5]]
            policy: HeuristicNextCardPolicy | DreamerNextCardPolicy = DreamerNextCardPolicy(
                self.model,
                opponents,
                fallback_ratings=self.ratings,
                synergy=self.synergy,
                synergy_scale=self.synergy_scale,
            )
        elif self._model_trained and len(self.league) > 0:
            opponents = [list(d.cards) for d in self.league.top(min(5, len(self.league)))]
            policy = DreamerNextCardPolicy(
                self.model,
                opponents,
                fallback_ratings=self.ratings,
                synergy=self.synergy,
                synergy_scale=self.synergy_scale,
            )
        else:
            jittered = {
                name: score + self.rng.uniform(-1.0, 1.0)
                for name, score in self.ratings.items()
            }
            policy = self._heuristic(jittered)
        return deck_from_policy(
            policy,
            self.pool,
            self.constraints,
            color_pips=self.color_pips,
            card_info=self.card_info,
        )

    def _seed_opponents(self, *, n: int, epoch: int) -> CardPool | None:
        if self.opponent_pool_factory is None:
            return None
        opp_pool = self.opponent_pool_factory(epoch)
        self._last_opponent_pool_size = sum(opp_pool.available.values())
        opp_ratings = default_ratings_for_pool(opp_pool)
        # Merge known hero ratings when names overlap (shared staples).
        for name, score in self.ratings.items():
            if name in opp_ratings:
                opp_ratings[name] = score
        seed_league_from_pool(
            self.league,
            self._heuristic(opp_ratings),
            opp_pool,
            self.constraints,
            n=n,
            rng=random.Random(self.seed + 10_000 + epoch),
            color_pips=self.color_pips,
            card_info=self.card_info,
            provenance=f"{OPPONENT_PROVENANCE}:epoch{epoch}",
            id_prefix=f"opp-e{epoch}",
        )
        return opp_pool

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
                    "opponent_epoch": self._opponent_epoch,
                },
            )

    def run(
        self,
        *,
        bootstrap_n: int = 3,
        max_challenges: int = 20,
    ) -> dict[str, Any]:
        opp_n = (
            self.opponent_bootstrap_n
            if self.opponent_bootstrap_n is not None
            else bootstrap_n
        )

        if self.opponent_pool_factory is not None:
            self._seed_opponents(n=opp_n, epoch=0)
        else:
            # Legacy: everyone shares the hero pool.
            seed_league_from_pool(
                self.league,
                self._heuristic(self.ratings),
                self.pool,
                self.constraints,
                n=bootstrap_n,
                rng=random.Random(self.seed),
                color_pips=self.color_pips,
                card_info=self.card_info,
            )

        job = OptimizationJob(
            self.league,
            self.oracle,
            self.stop_policy,
            games_per_match=self.games_per_match,
            seed=self.seed,
        )
        if self.opponent_pool_factory is not None:
            job.opponent_provenance_prefix = OPPONENT_PROVENANCE

        records_written = 0
        for _ in range(max(0, max_challenges)):
            cards = self._build_challenger()
            summary = job.challenge(cards, provenance="selfplay")
            self._record_from_summary(summary)
            records_written += 1
            games = int(summary["result"].get("games_played", 0))
            self._games_since_refresh += games

            if job.state.challenges % self.retrain_every == 0 and len(self.buffer) > 0:
                self.model.fit(self.buffer)
                self._model_trained = True

            if (
                self.opponent_pool_factory is not None
                and self._games_since_refresh >= self.opponent_refresh_games
            ):
                self.league.remove_by_provenance_prefix(OPPONENT_PROVENANCE)
                self._opponent_epoch += 1
                self._seed_opponents(n=opp_n, epoch=self._opponent_epoch)
                self._opponent_refresh_count += 1
                self._games_since_refresh = 0

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
                "provenance": d.provenance,
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
            "hero_pool_size": sum(self.pool.available.values()),
            "opponent_epoch": self._opponent_epoch,
            "opponent_refresh_count": self._opponent_refresh_count,
            "opponent_refresh_games": self.opponent_refresh_games,
            "last_opponent_pool_copies": self._last_opponent_pool_size,
        }
