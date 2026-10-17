#!/usr/bin/env python3
"""Continuous multi-agent sealed training with checkpoint resume.

Survives agent/process restarts: always ``--resume`` from the same checkpoint.

  PYTHONPATH=src python3 scripts/run_sealed_train_continuous.py
  PYTHONPATH=src python3 scripts/run_sealed_train_continuous.py --chunks 0   # forever
  PYTHONPATH=src python3 scripts/run_sealed_train_continuous.py --verify-every 10
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.meta.sealed_sim import (
    default_ratings_for_pool,
    generate_sealed_pool,
    load_union_pool,
    union_nonbasic_copies,
)
from magic_optimizer.selfplay.multi_agent import MultiAgentSealedLoop
from magic_optimizer.selfplay.oracle_factory import make_oracle

DEFAULT_CKPT = ROOT / "runs/sealed_multi_agent/checkpoint.json"
UNION = ROOT / "data/collections/union/union_collection.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", type=Path, default=DEFAULT_CKPT)
    ap.add_argument(
        "--backend",
        default="forge",
        choices=("stub", "forge"),
        help="Match oracle (default: forge; stub is hash-noise only)",
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-agents", type=int, default=3)
    ap.add_argument("--decks-per-agent", type=int, default=1)
    ap.add_argument("--games", type=int, default=5, help="Games per match")
    ap.add_argument("--refresh-games", type=int, default=100)
    ap.add_argument(
        "--chunk-games",
        type=int,
        default=100,
        help="Games to train per chunk before saving / looping",
    )
    ap.add_argument(
        "--chunks",
        type=int,
        default=0,
        help="Number of chunks to run (0 = forever until killed)",
    )
    ap.add_argument(
        "--target-copies",
        type=int,
        default=0,
        help="Sealed pool size (default: union nonbasic count)",
    )
    ap.add_argument("--hero-union", type=Path, default=UNION)
    ap.add_argument(
        "--verify-every",
        type=int,
        default=0,
        help="Run verify phase every N chunks (0 = never in this script)",
    )
    ap.add_argument("--verify-games", type=int, default=50)
    ap.add_argument("--records", type=Path, default=ROOT / "runs/sealed_multi_agent/matches.jsonl")
    ap.add_argument("--fresh", action="store_true", help="Ignore existing checkpoint")
    ap.add_argument(
        "--max-colors",
        type=int,
        default=3,
        help="Hard color-identity cap for built decks (0 = unlimited)",
    )
    args = ap.parse_args()

    if not args.hero_union.exists():
        print(f"error: union not found: {args.hero_union}", file=sys.stderr)
        return 2
    hero_pool = load_union_pool(args.hero_union)
    target = args.target_copies or union_nonbasic_copies(args.hero_union)

    def pool_factory(epoch: int, agent_id: int) -> CardPool:
        result = generate_sealed_pool(
            target_copies=target,
            seed=args.seed + 31 + epoch * 997 + agent_id * 13,
        )
        print(
            f"[sealed] epoch={epoch} agent={agent_id} "
            f"copies={result['total_copies']} unique={result['unique_cards']}",
            flush=True,
        )
        return CardPool(dict(result["pool"]))

    try:
        oracle = make_oracle(backend=args.backend, seed=args.seed)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    from magic_optimizer.deck_picker.card_info import make_card_info

    card_info = make_card_info(ROOT / "runs/card_color_cache.json")
    max_colors = None if args.max_colors <= 0 else args.max_colors

    print(f"backend={args.backend} max_colors={max_colors}", flush=True)

    loop = MultiAgentSealedLoop(
        oracle=oracle,
        pool_factory=pool_factory,
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        n_agents=args.n_agents,
        decks_per_agent=args.decks_per_agent,
        games_per_match=args.games,
        refresh_games=args.refresh_games,
        seed=args.seed,
        ratings_seed=default_ratings_for_pool(hero_pool),
        records_path=args.records,
        card_info=card_info,
        max_colors=max_colors,
    )
    loop.checkpoint_path = args.checkpoint

    if args.checkpoint.exists() and not args.fresh:
        loop.load_checkpoint(args.checkpoint)
        print(
            f"resumed checkpoint epoch={loop.epoch} games={loop.total_games} "
            f"replay={len(loop.buffer)}",
            flush=True,
        )
    else:
        print(f"starting fresh → {args.checkpoint}", flush=True)

    chunk_i = 0
    while args.chunks == 0 or chunk_i < args.chunks:
        chunk_i += 1
        t0 = time.time()
        summary = loop.run_train(
            additional_games=args.chunk_games,
            matches_per_epoch_cap=max(20, args.chunk_games // max(1, args.games)),
        )
        ckpt = loop.save_checkpoint()
        print(
            json.dumps(
                {
                    "chunk": chunk_i,
                    "epoch": summary["epoch"],
                    "total_games": summary["total_games"],
                    "refresh_count": summary["refresh_count"],
                    "replay_size": summary["replay_size"],
                    "model_trained": summary["model_trained"],
                    "checkpoint": str(ckpt),
                    "seconds": round(time.time() - t0, 2),
                }
            ),
            flush=True,
        )
        if args.verify_every and chunk_i % args.verify_every == 0:
            verify = loop.run_verify(hero_pool, max_games=args.verify_games)
            print(
                json.dumps(
                    {
                        "verify": True,
                        "hero_winrate": verify.get("hero_winrate"),
                        "hero_games": verify.get("hero_games"),
                        "total_games": loop.total_games,
                    }
                ),
                flush=True,
            )
            loop.save_checkpoint()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
