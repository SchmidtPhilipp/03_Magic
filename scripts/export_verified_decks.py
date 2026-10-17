#!/usr/bin/env python3
"""Load sealed multi-agent checkpoint, verify on union pool, export top decks.

  PYTHONPATH=src python3 scripts/export_verified_decks.py
  PYTHONPATH=src python3 scripts/export_verified_decks.py --top-k 5 --verify-games 100
"""
from __future__ import annotations

import argparse
import json
import sys
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
OUT = ROOT / "data/decks/verified"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", type=Path, default=DEFAULT_CKPT)
    ap.add_argument("--hero-union", type=Path, default=UNION)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument(
        "--backend",
        default="forge",
        choices=("stub", "forge"),
        help="Match oracle (default: forge)",
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-agents", type=int, default=3)
    ap.add_argument("--hero-decks", type=int, default=5)
    ap.add_argument("--verify-games", type=int, default=100)
    ap.add_argument("--refresh-games", type=int, default=50)
    ap.add_argument("--target-copies", type=int, default=0)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--min-games", type=int, default=5)
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--max-colors", type=int, default=3)
    args = ap.parse_args()

    if not args.checkpoint.exists():
        print(f"error: checkpoint missing: {args.checkpoint}", file=sys.stderr)
        return 2
    if not args.hero_union.exists():
        print(f"error: union missing: {args.hero_union}", file=sys.stderr)
        return 2

    hero_pool = load_union_pool(args.hero_union)
    target = args.target_copies or min(400, union_nonbasic_copies(args.hero_union))

    def pool_factory(epoch: int, agent_id: int) -> CardPool:
        result = generate_sealed_pool(
            target_copies=target,
            seed=args.seed + 71 + epoch * 997 + agent_id * 13,
        )
        return CardPool(dict(result["pool"]))

    from magic_optimizer.deck_picker.card_info import make_card_info

    oracle = make_oracle(backend=args.backend, seed=args.seed)
    max_colors = None if args.max_colors <= 0 else args.max_colors
    loop = MultiAgentSealedLoop(
        oracle=oracle,
        pool_factory=pool_factory,
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        n_agents=args.n_agents,
        decks_per_agent=1,
        games_per_match=args.games,
        refresh_games=args.refresh_games,
        seed=args.seed,
        ratings_seed=default_ratings_for_pool(hero_pool),
        card_info=make_card_info(ROOT / "runs/card_color_cache.json"),
        max_colors=max_colors,
    )
    loop.load_checkpoint(args.checkpoint)
    print(
        f"loaded checkpoint epoch={loop.epoch} games={loop.total_games} "
        f"replay={len(loop.buffer)}",
        flush=True,
    )
    verify = loop.run_verify(
        hero_pool,
        max_games=args.verify_games,
        hero_decks=args.hero_decks,
    )
    report = loop.export_verified_decks(
        args.out, top_k=args.top_k, min_games=args.min_games
    )
    print(
        json.dumps(
            {
                "hero_winrate": verify.get("hero_winrate"),
                "hero_games": verify.get("hero_games"),
                "hero_decks": verify.get("hero_decks"),
                "export": report,
            },
            indent=2,
        )
    )
    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
