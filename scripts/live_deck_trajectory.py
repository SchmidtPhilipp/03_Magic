#!/usr/bin/env python3
"""Build / modify decks with trajectory and resumable Deck-RL checkpoints.

Usage:
  # Fresh run, write checkpoint after each modify step
  PYTHONPATH=src python3 scripts/live_deck_trajectory.py \\
    --checkpoint runs/deck_rl.json --modify-steps 3

  # Resume deck RL loop from checkpoint (more swap iterations)
  PYTHONPATH=src python3 scripts/live_deck_trajectory.py \\
    --resume runs/deck_rl.json --modify-steps 5
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from collections import Counter
from pathlib import Path

try:
    from magic_optimizer.deck_picker import (
        BASIC_LANDS,
        CardRef,
        DeckConstraints,
        DeckRLState,
        HeuristicNextCardPolicy,
        apply_swap,
        complete_deck_with_trajectory,
        load_checkpoint,
        pool_from_card_rows,
        propose_swaps,
        save_checkpoint,
        steps_to_dicts,
    )
except ModuleNotFoundError:
    print("Run with PYTHONPATH=src and Python 3.11+", file=sys.stderr)
    raise


def pause(msg: str, sec: float = 0.08) -> None:
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


def run_modify_loop(
    state: DeckRLState,
    *,
    steps: int,
    checkpoint_path: Path | None,
) -> DeckRLState:
    policy = HeuristicNextCardPolicy(state.ratings)
    pool = state.card_pool()
    for i in range(max(0, steps)):
        swaps = propose_swaps(policy, pool, state.deck, state.constraints, k=5)
        if not swaps:
            pause(f"  iter {state.iteration}: keine weiteren positiven Swaps — stop")
            break
        best = swaps[0]
        pause(
            f"  iter {state.iteration}: − {best.remove.name} + {best.add.name} "
            f"(Δ={best.score_delta:+.1f})"
        )
        state.deck = apply_swap(state.deck, best)
        state.trajectory.append(
            {
                "action": "swap",
                "remove": best.remove.name,
                "add": best.add.name,
                "score_delta": best.score_delta,
            }
        )
        state.iteration += 1
        if checkpoint_path:
            save_checkpoint(checkpoint_path, state)
            pause(f"     💾 checkpoint → {checkpoint_path} (iteration={state.iteration})")
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collection",
        type=Path,
        default=Path("data/collections/collection_278079_69871_1751833200.csv"),
    )
    parser.add_argument("--seed-deck", type=Path, help="Optional seed deck (one name/line)")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("runs/deck_rl_checkpoint.json"),
        help="Where to write/update Deck-RL state",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        help="Resume from this checkpoint (skips fresh build)",
    )
    parser.add_argument(
        "--modify-steps",
        type=int,
        default=3,
        help="How many swap iterations of the deck RL loop to run",
    )
    args = parser.parse_args()

    if args.resume:
        pause(f"\n▶️  Resume Deck-RL from {args.resume}")
        state = load_checkpoint(args.resume)
        pause(
            f"   deck={len(state.deck)} cards  iteration={state.iteration}  "
            f"pool={len(state.pool)}"
        )
        # Write back to the resumed file unless --checkpoint was set explicitly
        # to something other than the default.
        default_ckpt = Path("runs/deck_rl_checkpoint.json")
        ckpt = args.resume if args.checkpoint == default_ckpt else args.checkpoint
        state = run_modify_loop(state, steps=args.modify_steps, checkpoint_path=ckpt)
        pause(f"\n✅ Resumed to iteration={state.iteration}  saved {ckpt}\n")
        return 0

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
        pause(f"🌱 Seed deck: {len(seed)} cards")

    pause("\n=== Trajektorie (build) ===")
    deck, steps = complete_deck_with_trajectory(
        policy, pool, constraints, seed_deck=seed or None, alt_k=2
    )
    for step in steps:
        if step.action == "fill_basics":
            continue
        pause(
            f"  [{step.index:02d}] {step.action:12} {step.card.name:<36} "
            f"score={step.score:5.2f}",
            0.03,
        )
    basics = sum(1 for c in deck if c.name in BASIC_LANDS)
    pause(f"  … + {basics} basics → {len(deck)} cards")

    state = DeckRLState(
        deck=deck,
        pool=dict(pool.available),
        constraints=constraints,
        ratings=ratings,
        iteration=0,
        trajectory=steps_to_dicts(steps),
        meta={"collection": str(args.collection)},
    )
    save_checkpoint(args.checkpoint, state)
    pause(f"\n💾 Initial checkpoint → {args.checkpoint}")

    pause("\n=== Deck-RL modify loop ===")
    state = run_modify_loop(
        state, steps=args.modify_steps, checkpoint_path=args.checkpoint
    )

    pause("\n=== Deck counts ===")
    for name, cnt in Counter(c.name for c in state.deck).most_common(10):
        pause(f"  {cnt}× {name}", 0.03)

    pause(
        f"\n✅ Done. Resume later with:\n"
        f"   PYTHONPATH=src python3 scripts/live_deck_trajectory.py "
        f"--resume {args.checkpoint} --modify-steps 5\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
