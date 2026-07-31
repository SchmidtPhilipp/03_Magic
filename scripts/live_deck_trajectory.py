#!/usr/bin/env python3
"""Live view: build from repo collection with trajectory, then modify the deck.

Usage:
  PYTHONPATH=src python3 scripts/live_deck_trajectory.py
  PYTHONPATH=src python3 scripts/live_deck_trajectory.py --collection data/collections/FinalFantasy.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from collections import Counter
from pathlib import Path

# Prefer loading without package __init__ if numpy missing — use normal import when possible.
try:
    from magic_optimizer.deck_picker import (
        BASIC_LANDS,
        CardRef,
        DeckConstraints,
        HeuristicNextCardPolicy,
        apply_swap,
        complete_deck_with_trajectory,
        pool_from_card_rows,
        propose_swaps,
    )
except ModuleNotFoundError:
    print("Run with PYTHONPATH=src and Python 3.11+", file=sys.stderr)
    raise


def pause(msg: str, sec: float = 0.12) -> None:
    print(msg, flush=True)
    time.sleep(sec)


def load_collection(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    out: list[dict] = []
    for r in rows:
        name = (r.get("card_name") or r.get("Name") or "").strip()
        if not name:
            continue
        amt = int(r.get("amount") or r.get("Quantity") or 1)
        out.append({"card_name": name, "amount": min(4, max(1, amt))})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collection",
        type=Path,
        default=Path("data/collections/collection_278079_69871_1751833200.csv"),
    )
    parser.add_argument("--seed-deck", type=Path, help="Optional text file: one card name per line")
    args = parser.parse_args()

    pause(f"\n📁 Collection: {args.collection}")
    rows = load_collection(args.collection)
    pool = pool_from_card_rows(rows)
    pause(f"   → {len(pool.available)} unique cards")

    ratings = {
        n: (int(hashlib.sha256(n.encode()).hexdigest()[:8], 16) % 1000) / 100.0
        for n in pool.available
    }
    policy = HeuristicNextCardPolicy(ratings)
    constraints = DeckConstraints(non_basic_target=40)

    seed: list[CardRef] = []
    if args.seed_deck and args.seed_deck.exists():
        seed = [
            CardRef(line.strip())
            for line in args.seed_deck.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        pause(f"🌱 Seed deck: {len(seed)} cards from {args.seed_deck}")

    pause("\n=== Trajektorie (build) ===")
    deck, steps = complete_deck_with_trajectory(
        policy, pool, constraints, seed_deck=seed or None, alt_k=2
    )
    for step in steps:
        if step.action == "fill_basics":
            continue  # summarize basics at end
        alts = ""
        if step.alternatives:
            alts = "  | alt: " + ", ".join(
                f"{a.card.name}({a.score:.1f})" for a in step.alternatives
            )
        pause(
            f"  [{step.index:02d}] {step.action:12} {step.card.name:<36} "
            f"score={step.score:5.2f}{alts}",
            0.05,
        )
    basics = sum(1 for c in deck if c.name in BASIC_LANDS)
    pause(f"  … + {basics} basic lands → Deck size {len(deck)}")

    pause("\n=== Fertiges Deck (Counts) ===")
    for name, cnt in Counter(c.name for c in deck).most_common(12):
        pause(f"  {cnt}× {name}", 0.04)

    pause("\n=== Modify: Swap-Vorschläge ===")
    swaps = propose_swaps(policy, pool, deck, constraints, k=5)
    if not swaps:
        pause("  (keine positiven Swaps)")
    for i, s in enumerate(swaps, 1):
        pause(
            f"  {i}. − {s.remove.name} ({s.remove_score:.1f})  "
            f"+ {s.add.name} ({s.add_score:.1f})  Δ={s.score_delta:+.1f}",
            0.1,
        )

    if swaps:
        pause("\n=== Apply besten Swap ===")
        before = Counter(c.name for c in deck)
        deck = apply_swap(deck, swaps[0])
        after = Counter(c.name for c in deck)
        pause(f"  entfernt: {swaps[0].remove.name} ({before[swaps[0].remove.name]}→{after[swaps[0].remove.name]})")
        pause(f"  hinzu:    {swaps[0].add.name} ({before[swaps[0].add.name]}→{after[swaps[0].add.name]})")

    pause("\n✅ Fertig. API: POST /api/deck-picker/complete {trajectory:true}")
    pause("         POST /api/deck-picker/modify  {decklist, pool, apply:true}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
