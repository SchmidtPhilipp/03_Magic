#!/usr/bin/env python3
"""CLI for Homelab / local self-play loop. Default backend is stub (CI-safe).

Env:
  SELFPLAY_BACKEND=stub|forge  (default stub)

Multi-agent sealed (recommended):
  Training — 3 agents, shared model, each gets a fresh sealed pool every refresh.
  Verify   — agent 0 locks to your union; others stay sealed-random.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.league.stop_policy import WinrateThresholdStop
from magic_optimizer.meta.sealed_sim import (
    default_ratings_for_pool,
    generate_sealed_pool,
    load_union_pool,
    union_nonbasic_copies,
)
from magic_optimizer.pool_prune.dominance import prune_superseded
from magic_optimizer.pool_prune.facts import CardFactsStore
from magic_optimizer.selfplay.loop import SelfPlayLoop
from magic_optimizer.selfplay.multi_agent import MultiAgentSealedLoop
from magic_optimizer.selfplay.oracle_factory import make_oracle
from magic_optimizer.synergy.learn import learn_synergy_from_jsonl

UNION_DEFAULT = ROOT / "data/collections/union/union_collection.csv"


def _demo_pool(n: int = 40) -> tuple[CardPool, dict[str, float]]:
    pool = CardPool({f"Card{i}": 4 for i in range(n)})
    ratings = {f"Card{i}": float(i) for i in range(n)}
    return pool, ratings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run league↔oracle↔Dreamer self-play")
    parser.add_argument("--backend", default=os.environ.get("SELFPLAY_BACKEND", "stub"))
    parser.add_argument("--bootstrap-n", type=int, default=3)
    parser.add_argument("--max-challenges", type=int, default=10)
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--retrain-every", type=int, default=2)
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--min-games", type=int, default=20)
    parser.add_argument("--records", default="runs/selfplay_matches.jsonl")
    parser.add_argument("--pool-json", default="", help="Optional JSON {pool, ratings}")
    parser.add_argument(
        "--multi-agent-sealed",
        action="store_true",
        help="3 agents, shared knowledge, random sealed pools in train; verify with union",
    )
    parser.add_argument("--n-agents", type=int, default=3)
    parser.add_argument("--decks-per-agent", type=int, default=2)
    parser.add_argument(
        "--refresh-games",
        type=int,
        default=100,
        help="Regenerate all sealed pools after this many games",
    )
    parser.add_argument(
        "--train-games",
        type=int,
        default=500,
        help="Total games in symmetric training phase",
    )
    parser.add_argument(
        "--verify-games",
        type=int,
        default=100,
        help="Games in verification phase (hero=union). 0 skips verify.",
    )
    parser.add_argument(
        "--hero-union",
        default=str(UNION_DEFAULT),
        help="Union CSV used only in verify phase",
    )
    parser.add_argument(
        "--opponent-target-copies",
        type=int,
        default=0,
        help="Sealed pool size target (default: union nonbasic copies)",
    )
    # legacy single-hero path (kept for old scripts)
    parser.add_argument(
        "--opponent-sealed",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--opponent-refresh-games", type=int, default=100)
    parser.add_argument(
        "--prune-superseded",
        action="store_true",
        help="Drop strictly dominated cards from the pool via CardFacts",
    )
    parser.add_argument("--facts-cache", default="runs/card_facts_cache.json")
    parser.add_argument("--synergy-jsonl", default="")
    parser.add_argument("--synergy-scale", type=float, default=0.1)
    args = parser.parse_args(argv)

    if args.opponent_sealed and not args.multi_agent_sealed:
        print(
            "note: --opponent-sealed is deprecated; using --multi-agent-sealed",
            file=sys.stderr,
        )
        args.multi_agent_sealed = True

    try:
        oracle = make_oracle(backend=args.backend, seed=args.seed)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    synergy = None
    if args.synergy_jsonl:
        synergy = learn_synergy_from_jsonl(args.synergy_jsonl)

    if args.multi_agent_sealed:
        hero_path = Path(args.hero_union)
        if not hero_path.exists():
            print(f"error: hero union not found: {hero_path}", file=sys.stderr)
            return 2
        hero_pool = load_union_pool(hero_path)
        target = args.opponent_target_copies or union_nonbasic_copies(hero_path)

        def pool_factory(epoch: int, agent_id: int) -> CardPool:
            result = generate_sealed_pool(
                target_copies=target,
                seed=args.seed + 31 + epoch * 997 + agent_id * 13,
            )
            print(
                f"[sealed] epoch={epoch} agent={agent_id} "
                f"copies={result['total_copies']} unique={result['unique_cards']}",
                file=sys.stderr,
            )
            return CardPool(dict(result["pool"]))

        loop = MultiAgentSealedLoop(
            oracle=oracle,
            pool_factory=pool_factory,
            constraints=DeckConstraints(deck_size=60, non_basic_target=40),
            n_agents=args.n_agents,
            decks_per_agent=args.decks_per_agent,
            games_per_match=args.games,
            refresh_games=args.refresh_games,
            seed=args.seed,
            retrain_every=args.retrain_every,
            ratings_seed=default_ratings_for_pool(hero_pool),
            synergy=synergy,
            synergy_scale=args.synergy_scale,
            records_path=args.records,
        )
        train = loop.run_train(max_games=args.train_games)
        out: dict = {"train": train}
        if args.verify_games > 0:
            out["verify"] = loop.run_verify(hero_pool, max_games=args.verify_games)
        if synergy is not None:
            out["synergy_edges"] = len(synergy)
        print(json.dumps(out, indent=2))
        return 0

    # ---- legacy single-pool loop ----
    if args.pool_json:
        payload = json.loads(Path(args.pool_json).read_text(encoding="utf-8"))
        pool = CardPool({str(k): int(v) for k, v in payload["pool"].items()})
        ratings = {str(k): float(v) for k, v in (payload.get("ratings") or {}).items()}
    else:
        pool, ratings = _demo_pool()

    prune_report = None
    if args.prune_superseded:
        store = CardFactsStore(cache_path=args.facts_cache)
        facts = store.get_many(pool.available.keys())
        pool, prune_report = prune_superseded(pool, facts)

    loop = SelfPlayLoop(
        oracle=oracle,
        stop_policy=WinrateThresholdStop(
            threshold=args.threshold, min_games=args.min_games
        ),
        pool=pool,
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        ratings=ratings,
        records_path=args.records,
        games_per_match=args.games,
        seed=args.seed,
        retrain_every=args.retrain_every,
        synergy=synergy,
        synergy_scale=args.synergy_scale,
    )
    result = loop.run(
        bootstrap_n=args.bootstrap_n, max_challenges=args.max_challenges
    )
    if prune_report is not None:
        result["prune"] = {
            "dropped_count": prune_report["dropped_count"],
            "kept_pool_size": prune_report["kept_pool_size"],
        }
    if synergy is not None:
        result["synergy_edges"] = len(synergy)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
