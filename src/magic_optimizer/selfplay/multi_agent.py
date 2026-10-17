"""Multi-agent sealed self-play: shared knowledge, private random pools.

Training: every agent draws a fresh sealed pool each epoch (symmetric).
Verification: one agent locks to a fixed hero pool; others stay sealed-random.

Checkpoints (`save_checkpoint` / `load_checkpoint`) let training survive process
restarts — resume model, replay, counters, and RNG.
"""
from __future__ import annotations

import json
import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints
from magic_optimizer.dreamer.replay import ReplayBuffer, Transition
from magic_optimizer.dreamer.world_model import WorldModel
from magic_optimizer.league.bootstrap import deck_from_policy
from magic_optimizer.league.elo import update_elo
from magic_optimizer.league.store import League
from magic_optimizer.league.types import LeagueDeck
from magic_optimizer.match_oracle.records import append_match_record
from magic_optimizer.match_oracle.types import MatchOracle
from magic_optimizer.meta.sealed_sim import default_ratings_for_pool
from magic_optimizer.synergy.graph import SynergyGraph

CHECKPOINT_VERSION = 1


@dataclass
class AgentState:
    agent_id: int
    pool: CardPool
    ratings: dict[str, float] = field(default_factory=dict)
    deck_ids: list[str] = field(default_factory=list)
    fixed_pool: bool = False


class MultiAgentSealedLoop:
    """3+ agents, shared WorldModel/Synergy, per-agent sealed inventories."""

    def __init__(
        self,
        *,
        oracle: MatchOracle,
        pool_factory: Callable[[int, int], CardPool],
        constraints: DeckConstraints,
        n_agents: int = 3,
        decks_per_agent: int = 2,
        games_per_match: int = 5,
        refresh_games: int = 100,
        seed: int = 0,
        retrain_every: int = 50,
        dim: int = 64,
        ratings_seed: dict[str, float] | None = None,
        synergy: SynergyGraph | None = None,
        synergy_scale: float = 0.1,
        records_path: str | Path | None = None,
        card_info: Callable[[str], dict | None] | None = None,
        color_pips: dict[str, int] | None = None,
        max_colors: int | None = 3,
        allowed_colors: frozenset[str] | None = None,
    ) -> None:
        if n_agents < 2:
            raise ValueError("n_agents must be >= 2")
        self.oracle = oracle
        self.pool_factory = pool_factory
        # Copy constraints and apply color limits (modifiable hard cap).
        self.constraints = DeckConstraints(
            deck_size=constraints.deck_size,
            max_copies=constraints.max_copies,
            banned=constraints.banned,
            pinned=constraints.pinned,
            non_basic_target=constraints.non_basic_target,
            max_colors=(
                max_colors
                if max_colors is not None
                else constraints.max_colors
            ),
            allowed_colors=(
                allowed_colors
                if allowed_colors is not None
                else constraints.allowed_colors
            ),
        )
        self.n_agents = n_agents
        self.decks_per_agent = max(1, decks_per_agent)
        self.games_per_match = games_per_match
        self.refresh_games = max(1, refresh_games)
        self.seed = seed
        self.retrain_every = max(1, retrain_every)
        self.ratings_seed = dict(ratings_seed or {})
        self.synergy = synergy
        self.synergy_scale = float(synergy_scale)
        self.records_path = Path(records_path) if records_path else None
        self.card_info = card_info
        self.color_pips = color_pips
        self.rng = random.Random(seed)
        self.league = League()
        self.buffer = ReplayBuffer()
        self.model = WorldModel(dim=dim, seed=seed)
        self._model_trained = False
        self.agents: list[AgentState] = []
        self.epoch = 0
        self.total_games = 0
        self.refresh_count = 0
        self.checkpoint_path: Path | None = None

    def save_checkpoint(self, path: str | Path | None = None) -> Path:
        """Persist shared knowledge + training counters (not current sealed pools)."""
        target = Path(path or self.checkpoint_path or "runs/sealed_multi_agent/checkpoint.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CHECKPOINT_VERSION,
            "epoch": self.epoch,
            "total_games": self.total_games,
            "refresh_count": self.refresh_count,
            "n_agents": self.n_agents,
            "decks_per_agent": self.decks_per_agent,
            "games_per_match": self.games_per_match,
            "refresh_games": self.refresh_games,
            "seed": self.seed,
            "retrain_every": self.retrain_every,
            "synergy_scale": self.synergy_scale,
            "model_trained": self._model_trained,
            "rng_state": list(self.rng.getstate()[1]),
            "rng_version": int(self.rng.getstate()[0]),
            "rng_gauss": self.rng.getstate()[2],
            "model": self.model.to_dict(),
            "replay": [
                {
                    "deck_a": list(t.deck_a),
                    "deck_b": list(t.deck_b),
                    "winrate_a": t.winrate_a,
                }
                for t in self.buffer.as_list()
            ],
            "ratings_seed": self.ratings_seed,
        }
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(target)
        self.checkpoint_path = target
        meta = target.with_name("checkpoint_meta.json")
        meta.write_text(
            json.dumps(
                {
                    "path": str(target),
                    "epoch": self.epoch,
                    "total_games": self.total_games,
                    "refresh_count": self.refresh_count,
                    "replay_size": len(self.buffer),
                    "model_trained": self._model_trained,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return target

    def load_checkpoint(self, path: str | Path) -> None:
        """Restore model/replay/counters/RNG from a prior `save_checkpoint`."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if int(data.get("version", 0)) != CHECKPOINT_VERSION:
            raise ValueError(f"unsupported checkpoint version: {data.get('version')}")
        self.epoch = int(data["epoch"])
        self.total_games = int(data["total_games"])
        self.refresh_count = int(data["refresh_count"])
        self._model_trained = bool(data.get("model_trained", False))
        self.model = WorldModel.from_dict(data["model"])
        self.buffer = ReplayBuffer()
        self.buffer.extend_from_records(list(data.get("replay") or []))
        if data.get("ratings_seed"):
            self.ratings_seed = {str(k): float(v) for k, v in data["ratings_seed"].items()}
        # Restore RNG (Python 3 Random state tuple)
        state = (
            int(data.get("rng_version", 3)),
            tuple(int(x) for x in data["rng_state"]),
            data.get("rng_gauss"),
        )
        self.rng.setstate(state)
        self.checkpoint_path = Path(path)

    def _ratings_for(self, pool: CardPool) -> dict[str, float]:
        ratings = default_ratings_for_pool(pool)
        for name, score in self.ratings_seed.items():
            if name in ratings:
                ratings[name] = score
        return ratings

    def _heuristic(self, ratings: dict[str, float]) -> HeuristicNextCardPolicy:
        return HeuristicNextCardPolicy(
            ratings,
            synergy=self.synergy,
            synergy_scale=self.synergy_scale,
        )

    def _policy_for(self, agent: AgentState) -> HeuristicNextCardPolicy:
        # Heuristic only for deck construction: sealed epochs reshuffle card
        # namespaces, so Dreamer-on-disjoint-names can hang / mis-score.
        # WorldModel still trains on match outcomes for later shared transfer.
        jittered = {
            n: s + self.rng.uniform(-1.0, 1.0) for n, s in agent.ratings.items()
        }
        return self._heuristic(jittered)

    def _clear_agent_decks(self) -> None:
        for agent in self.agents:
            for did in agent.deck_ids:
                self.league.remove(did)
            agent.deck_ids.clear()

    def _assign_pools(
        self,
        *,
        epoch: int,
        hero_pool: CardPool | None,
        hero_agent_id: int = 0,
    ) -> None:
        self.agents = []
        for i in range(self.n_agents):
            if hero_pool is not None and i == hero_agent_id:
                pool = hero_pool
                fixed = True
            else:
                pool = self.pool_factory(epoch, i)
                fixed = False
            self.agents.append(
                AgentState(
                    agent_id=i,
                    pool=pool,
                    ratings=self._ratings_for(pool),
                    fixed_pool=fixed,
                )
            )

    def _build_all_decks(self) -> None:
        self._clear_agent_decks()
        for agent in self.agents:
            for k in range(self.decks_per_agent):
                policy = self._policy_for(agent)
                cards = deck_from_policy(
                    policy,
                    agent.pool,
                    self.constraints,
                    color_pips=self.color_pips,
                    card_info=self.card_info,
                )
                did = f"a{agent.agent_id}-e{self.epoch}-d{k}-{uuid.uuid4().hex[:6]}"
                self.league.add(
                    LeagueDeck(
                        id=did,
                        cards=cards,
                        elo=1000.0 + self.rng.uniform(-15, 15),
                        provenance=(
                            f"agent:{agent.agent_id}:fixed"
                            if agent.fixed_pool
                            else f"agent:{agent.agent_id}:sealed"
                        ),
                    )
                )
                agent.deck_ids.append(did)

    def _play_pair(self, deck_a_id: str, deck_b_id: str) -> dict[str, Any]:
        a = self.league.get(deck_a_id)
        b = self.league.get(deck_b_id)
        result = self.oracle.play(
            [CardRef(n) for n in a.cards],
            [CardRef(n) for n in b.cards],
            games=self.games_per_match,
        )
        if result.wins_a > result.wins_b:
            self.league.record_match(
                deck_a_id,
                deck_b_id,
                games=result.games_played,
                wins_winner=result.wins_a,
                wins_loser=result.wins_b,
            )
        elif result.wins_b > result.wins_a:
            self.league.record_match(
                deck_b_id,
                deck_a_id,
                games=result.games_played,
                wins_winner=result.wins_b,
                wins_loser=result.wins_a,
            )
        else:
            a.games += result.games_played
            b.games += result.games_played
            # still nudge elo slightly toward draw
            aw, bw = update_elo(a.elo, b.elo, 0.5)
            a.elo, b.elo = aw, bw

        wr = (
            result.wins_a / result.games_played if result.games_played else 0.5
        )
        self.buffer.add(
            Transition(
                deck_a=tuple(a.cards),
                deck_b=tuple(b.cards),
                winrate_a=wr,
            )
        )
        if self.records_path is not None:
            self.records_path.parent.mkdir(parents=True, exist_ok=True)
            append_match_record(
                self.records_path,
                {
                    "deck_a": list(a.cards),
                    "deck_b": list(b.cards),
                    "wins_a": result.wins_a,
                    "wins_b": result.wins_b,
                    "games_played": result.games_played,
                    "winrate_a": wr,
                    "engine": result.engine,
                    "deck_a_id": deck_a_id,
                    "deck_b_id": deck_b_id,
                    "epoch": self.epoch,
                    "phase": "train" if not any(x.fixed_pool for x in self.agents) else "verify",
                },
            )
        self.total_games += result.games_played
        return {
            "wins_a": result.wins_a,
            "wins_b": result.wins_b,
            "games_played": result.games_played,
        }

    def _matches_until_refresh(self, *, max_matches: int) -> int:
        """Play random cross-agent matches; return matches played."""
        played = 0
        games_at_epoch_start = self.total_games
        while played < max_matches:
            if self.total_games - games_at_epoch_start >= self.refresh_games:
                break
            # pick two different agents that have decks
            alive = [a for a in self.agents if a.deck_ids]
            if len(alive) < 2:
                break
            a1, a2 = self.rng.sample(alive, 2)
            d1 = self.rng.choice(a1.deck_ids)
            d2 = self.rng.choice(a2.deck_ids)
            self._play_pair(d1, d2)
            played += 1
            if played % self.retrain_every == 0 and len(self.buffer) > 0:
                self.model.fit(self.buffer)
                self._model_trained = True
        return played

    def run_train(
        self,
        *,
        max_games: int | None = None,
        additional_games: int | None = None,
        matches_per_epoch_cap: int = 50,
        checkpoint_every_epoch: bool = True,
    ) -> dict[str, Any]:
        """Symmetric training: all agents get random sealed pools each epoch.

        Use ``additional_games`` for resume-friendly chunks (target =
        current total_games + additional). ``max_games`` is an absolute
        ceiling on ``total_games``.
        """
        if additional_games is not None:
            target = self.total_games + max(0, int(additional_games))
        elif max_games is not None:
            target = int(max_games)
        else:
            target = self.total_games + 500
        matches_total = 0
        while self.total_games < target:
            self._assign_pools(epoch=self.epoch, hero_pool=None)
            self._build_all_decks()
            played = self._matches_until_refresh(max_matches=matches_per_epoch_cap)
            matches_total += played
            if played == 0:
                break
            self.epoch += 1
            self.refresh_count += 1
            if len(self.buffer) > 0:
                self.model.fit(self.buffer)
                self._model_trained = True
            if checkpoint_every_epoch and self.checkpoint_path is not None:
                self.save_checkpoint()
        if self.checkpoint_path is not None:
            self.save_checkpoint()
        return self._summary(phase="train", matches_total=matches_total)

    def run_verify(
        self,
        hero_pool: CardPool,
        *,
        max_games: int = 100,
        matches_per_epoch_cap: int = 40,
        hero_agent_id: int = 0,
        hero_decks: int | None = None,
    ) -> dict[str, Any]:
        """Hold out: hero_agent uses fixed pool; others keep sealed-random refreshes.

        Tracks per-hero-deck win stats in ``self.last_verify_decks`` for export.
        """
        verify_start_games = self.total_games
        matches_total = 0
        hero_wins = 0
        hero_games = 0
        # Stable hero decks for the whole verify run (opponents still refresh).
        n_hero = hero_decks if hero_decks is not None else self.decks_per_agent
        self._assign_pools(
            epoch=self.epoch, hero_pool=hero_pool, hero_agent_id=hero_agent_id
        )
        hero = self.agents[hero_agent_id]
        # Build only hero decks once; keep ids across opponent refreshes.
        saved_decks_per = self.decks_per_agent
        self.decks_per_agent = max(1, n_hero)
        self._clear_agent_decks()
        # Build hero decks
        for k in range(self.decks_per_agent):
            policy = self._policy_for(hero)
            cards = deck_from_policy(
                policy,
                hero.pool,
                self.constraints,
                color_pips=self.color_pips,
                card_info=self.card_info,
            )
            did = f"hero-v-d{k}-{uuid.uuid4().hex[:6]}"
            self.league.add(
                LeagueDeck(
                    id=did,
                    cards=cards,
                    elo=1000.0,
                    provenance=f"agent:{hero_agent_id}:fixed",
                )
            )
            hero.deck_ids.append(did)
        self.decks_per_agent = saved_decks_per

        deck_stats: dict[str, dict[str, Any]] = {
            did: {
                "id": did,
                "wins": 0,
                "losses": 0,
                "games": 0,
                "cards": list(self.league.get(did).cards),
            }
            for did in hero.deck_ids
        }

        while self.total_games - verify_start_games < max_games:
            # Refresh only non-hero agent pools/decks
            for a in self.agents:
                if a.agent_id == hero_agent_id:
                    continue
                for did in list(a.deck_ids):
                    self.league.remove(did)
                a.deck_ids.clear()
                a.pool = self.pool_factory(self.epoch, a.agent_id)
                a.ratings = self._ratings_for(a.pool)
                a.fixed_pool = False
                for k in range(saved_decks_per):
                    policy = self._policy_for(a)
                    cards = deck_from_policy(
                        policy,
                        a.pool,
                        self.constraints,
                        color_pips=self.color_pips,
                        card_info=self.card_info,
                    )
                    did = f"a{a.agent_id}-e{self.epoch}-d{k}-{uuid.uuid4().hex[:6]}"
                    self.league.add(
                        LeagueDeck(
                            id=did,
                            cards=cards,
                            elo=1000.0 + self.rng.uniform(-15, 15),
                            provenance=f"agent:{a.agent_id}:sealed",
                        )
                    )
                    a.deck_ids.append(did)

            games_before = self.total_games
            others = [
                a for a in self.agents if a.agent_id != hero_agent_id and a.deck_ids
            ]
            played = 0
            while (
                played < matches_per_epoch_cap
                and self.total_games - verify_start_games < max_games
                and self.total_games - games_before < self.refresh_games
                and hero.deck_ids
                and others
            ):
                d1 = self.rng.choice(hero.deck_ids)
                opp = self.rng.choice(others)
                d2 = self.rng.choice(opp.deck_ids)
                summary = self._play_pair(d1, d2)
                hero_games += summary["games_played"]
                hero_wins += summary["wins_a"]
                st = deck_stats[d1]
                st["games"] += summary["games_played"]
                if summary["wins_a"] > summary["wins_b"]:
                    st["wins"] += 1
                elif summary["wins_b"] > summary["wins_a"]:
                    st["losses"] += 1
                played += 1
                matches_total += 1
                if played % self.retrain_every == 0 and len(self.buffer) > 0:
                    self.model.fit(self.buffer)
                    self._model_trained = True
            if played == 0:
                break
            self.epoch += 1
            self.refresh_count += 1

        ranked = sorted(
            deck_stats.values(),
            key=lambda s: (
                -(s["wins"] / s["games"] if s["games"] else 0.0),
                -s["wins"],
                -s["games"],
                s["id"],
            ),
        )
        for s in ranked:
            s["winrate"] = (s["wins"] / (s["wins"] + s["losses"])) if (
                s["wins"] + s["losses"]
            ) else None
            try:
                s["elo"] = self.league.get(s["id"]).elo
            except KeyError:
                s["elo"] = None
        self.last_verify_decks = ranked
        out = self._summary(phase="verify", matches_total=matches_total)
        out["hero_agent_id"] = hero_agent_id
        out["hero_pool_copies"] = sum(hero_pool.available.values())
        out["hero_games"] = hero_games
        out["hero_wins"] = hero_wins
        out["hero_winrate"] = (hero_wins / hero_games) if hero_games else None
        out["hero_decks"] = [
            {
                "id": s["id"],
                "wins": s["wins"],
                "losses": s["losses"],
                "games": s["games"],
                "winrate": s["winrate"],
                "elo": s["elo"],
            }
            for s in ranked
        ]
        return out

    def export_verified_decks(
        self,
        out_dir: str | Path,
        *,
        top_k: int = 5,
        min_games: int = 5,
    ) -> dict[str, Any]:
        """Write best hero decks from the last ``run_verify`` as .txt + report.json."""
        from collections import Counter

        decks = getattr(self, "last_verify_decks", None) or []
        eligible = [d for d in decks if d.get("games", 0) >= min_games] or list(decks)
        chosen = eligible[: max(0, top_k)]
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.txt"):
            old.unlink()
        exported = []
        for i, d in enumerate(chosen, 1):
            counts = Counter(d["cards"])
            lines = [
                f"{q} {n}"
                for n, q in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
            ]
            wr = d.get("winrate")
            wr_s = f"{wr:.0%}" if isinstance(wr, float) else "n/a"
            fname = f"{i:02d}_verified_wr{wr_s.replace('%', '')}_g{d['games']}.txt"
            # sanitize filename
            fname = fname.replace("/", "_")
            path = out / fname
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            exported.append(
                {
                    "file": str(path),
                    "id": d["id"],
                    "wins": d["wins"],
                    "losses": d["losses"],
                    "games": d["games"],
                    "winrate": d.get("winrate"),
                    "elo": d.get("elo"),
                    "size": sum(counts.values()),
                }
            )
        report = {
            "exported": exported,
            "top_k": top_k,
            "min_games": min_games,
            "total_candidates": len(decks),
        }
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (out / "README.txt").write_text(
            "\n".join(
                [
                    "Verified hero decks (union pool vs sealed opponents)",
                    *[
                        f"  - {Path(e['file']).name}  wr={e['winrate']}  "
                        f"{e['wins']}-{e['losses']} ({e['games']} games)"
                        for e in exported
                    ],
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return report

    def _summary(self, *, phase: str, matches_total: int) -> dict[str, Any]:
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
            "phase": phase,
            "n_agents": self.n_agents,
            "epoch": self.epoch,
            "refresh_count": self.refresh_count,
            "refresh_games": self.refresh_games,
            "total_games": self.total_games,
            "matches_total": matches_total,
            "model_trained": self._model_trained,
            "replay_size": len(self.buffer),
            "league_size": len(self.league),
            "standings": standings,
            "agent_pools": [
                {
                    "agent_id": a.agent_id,
                    "fixed": a.fixed_pool,
                    "copies": sum(a.pool.available.values()),
                    "unique": len(a.pool.available),
                    "decks": len(a.deck_ids),
                }
                for a in self.agents
            ],
        }
