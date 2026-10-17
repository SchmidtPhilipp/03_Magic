#!/usr/bin/env python3
"""Stochastic sealed pools from confirmed playgroup sets until ~union size.

Usage:
  PYTHONPATH=src python3 scripts/simulate_sealed_pool.py
  PYTHONPATH=src python3 scripts/simulate_sealed_pool.py --target-copies 1400 --seed 7
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.meta.sealed_sim import (  # noqa: E402
    generate_sealed_pool,
    load_confirmed_sets,
    union_nonbasic_copies,
)

OUT_DIR = ROOT / "data/meta/simulated_pools"
UNION = ROOT / "data/collections/union/union_collection.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-copies", type=int, default=0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--players", type=int, default=5)
    ap.add_argument("--packs-per-player", type=int, default=6)
    ap.add_argument("--promo-rate", type=float, default=0.25)
    args = ap.parse_args()
    target = args.target_copies or union_nonbasic_copies(UNION)
    print(f"Target nonbasic copies ≈ {target}")
    print(f"Sets: {', '.join(load_confirmed_sets())}")
    result = generate_sealed_pool(
        target_copies=target,
        seed=args.seed,
        players=args.players,
        packs_per_player=args.packs_per_player,
        promo_rate=args.promo_rate,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"sealed_sim_seed{result['seed']}_n{result['total_copies']}"
    json_path = OUT_DIR / f"{stem}.json"
    csv_path = OUT_DIR / f"{stem}.csv"
    # expand pool dict to list for readability
    payload = dict(result)
    payload["pool"] = [
        {"qty": q, "name": n}
        for n, q in sorted(result["pool"].items(), key=lambda x: (-x[1], x[0]))
    ]
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["amount", "card_name"])
        w.writeheader()
        for row in payload["pool"]:
            w.writerow({"amount": row["qty"], "card_name": row["name"]})
    (OUT_DIR / "latest.json").write_text(
        json.dumps(
            {
                "json": str(json_path.relative_to(ROOT)),
                "csv": str(csv_path.relative_to(ROOT)),
                "total_copies": result["total_copies"],
                "unique_cards": result["unique_cards"],
                "events": result["events"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Done: unique={result['unique_cards']} copies={result['total_copies']} "
        f"events={result['events']} packs={result['packs_opened']} "
        f"promos={result['promos_injected']}"
    )
    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
