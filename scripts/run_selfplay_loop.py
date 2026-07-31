#!/usr/bin/env python3
"""CLI for Homelab / local self-play loop. Default backend is stub (CI-safe).

Env:
  SELFPLAY_BACKEND=stub|forge  (default stub)
  Does not SSH or heal Forge — forge backend fails if forge_available() is false.
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
from magic_optimizer.selfplay.loop import SelfPlayLoop
from magic_optimizer.selfplay.oracle_factory import make_oracle


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
    args = parser.parse_args(argv)

    if args.pool_json:
        payload = json.loads(Path(args.pool_json).read_text(encoding="utf-8"))
        pool = CardPool({str(k): int(v) for k, v in payload["pool"].items()})
        ratings = {str(k): float(v) for k, v in (payload.get("ratings") or {}).items()}
    else:
        pool, ratings = _demo_pool()

    try:
        oracle = make_oracle(backend=args.backend, seed=args.seed)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

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
    )
    result = loop.run(
        bootstrap_n=args.bootstrap_n, max_challenges=args.max_challenges
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
