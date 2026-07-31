#!/usr/bin/env python3
"""Build / modify decks with trajectory, color-aware lands, resumable checkpoints.

NOTE: This loop optimizes a *heuristic rating*, not Forge winrate. Lands follow
mana pips from Scryfall when available — still not a global optimum.

Usage:
  PYTHONPATH=src python3 scripts/live_deck_trajectory.py --checkpoint runs/deck_rl.json
  PYTHONPATH=src python3 scripts/live_deck_trajectory.py --resume runs/deck_rl.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests

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
    from magic_optimizer.deck_picker.complete import refill_basics
    from magic_optimizer.deck_picker.mana import estimate_deck_color_pips
except ModuleNotFoundError:
    print("Run with PYTHONPATH=src and Python 3.11+", file=sys.stderr)
    raise


def pause(msg: str, sec: float = 0.05) -> None:
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


class ScryfallCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, dict] = {}
        if path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._data = {}

    def get(self, name: str) -> dict | None:
        if name in self._data:
            return self._data[name] or None
        try:
            r = requests.get(
                "https://api.scryfall.com/cards/named",
                params={"fuzzy": name},
                timeout=15,
                headers={
                    "User-Agent": "phi-labs-magic-optimizer/0.1 (deck-picker land fill)",
                    "Accept": "application/json",
                },
            )
            time.sleep(0.08)  # be nice to Scryfall
            if r.status_code == 200:
                payload = r.json()
                slim = {
                    "mana_cost": payload.get("mana_cost"),
                    "color_identity": payload.get("color_identity"),
                    "colors": payload.get("colors"),
                    "card_faces": [
                        {"mana_cost": f.get("mana_cost")}
                        for f in (payload.get("card_faces") or [])
                    ]
                    or None,
                }
                self._data[name] = slim
            else:
                self._data[name] = {}
        except requests.RequestException:
            self._data[name] = {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data), encoding="utf-8")
        return self._data[name] or None


def run_modify_loop(
    state: DeckRLState,
    *,
    steps: int,
    checkpoint_path: Path | None,
    card_info,
) -> DeckRLState:
    policy = HeuristicNextCardPolicy(state.ratings)
    pool = state.card_pool()
    for _ in range(max(0, steps)):
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
        # Rebuild mana base after each swap
        pips = estimate_deck_color_pips(state.deck, card_info=card_info)
        state.deck = refill_basics(state.deck, state.constraints, color_pips=pips)
        pause(f"     mana pips {pips} → basics refreshed")
        state.trajectory.append(
            {
                "action": "swap",
                "remove": best.remove.name,
                "add": best.add.name,
                "score_delta": best.score_delta,
                "color_pips": pips,
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
    parser.add_argument("--seed-deck", type=Path)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("runs/deck_rl_checkpoint.json"),
    )
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--modify-steps", type=int, default=5)
    parser.add_argument(
        "--scryfall-cache",
        type=Path,
        default=Path("runs/scryfall_cache.json"),
    )
    args = parser.parse_args()

    scry = ScryfallCache(args.scryfall_cache)
    pause(
        "⚠️  Heuristik-Loop (kein Forge-Winrate). Lands folgen Scryfall-Pips."
    )

    if args.resume:
        pause(f"\n▶️  Resume from {args.resume}")
        state = load_checkpoint(args.resume)
        default_ckpt = Path("runs/deck_rl_checkpoint.json")
        ckpt = args.resume if args.checkpoint == default_ckpt else args.checkpoint
        state = run_modify_loop(
            state,
            steps=args.modify_steps,
            checkpoint_path=ckpt,
            card_info=scry.get,
        )
        pause(f"\n✅ iteration={state.iteration}  saved {ckpt}\n")
        _print_deck(state.deck)
        return 0

    pause(f"\n📁 Collection: {args.collection}")
    rows = load_collection(args.collection)
    pool = pool_from_card_rows(rows)
    pause(f"   → {len(pool.available)} unique")

    ratings = {
        n: (int(hashlib.sha256(n.encode()).hexdigest()[:8], 16) % 1000) / 100.0
        for n in pool.available
    }
    # Prefetch scryfall for pool (rate-limited)
    pause("🔎 Scryfall color/mana lookup for pool…")
    for i, name in enumerate(sorted(pool.available)):
        scry.get(name)
        if (i + 1) % 50 == 0:
            pause(f"   … {i+1}/{len(pool.available)}")

    policy = HeuristicNextCardPolicy(ratings)
    constraints = DeckConstraints(non_basic_target=40)
    seed: list[CardRef] = []
    if args.seed_deck and args.seed_deck.exists():
        seed = [
            CardRef(line.strip())
            for line in args.seed_deck.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        pause(f"🌱 Seed: {len(seed)} cards")

    pause("\n=== Build + color-aware basics ===")
    deck, steps = complete_deck_with_trajectory(
        policy,
        pool,
        constraints,
        seed_deck=seed or None,
        alt_k=2,
        card_info=scry.get,
    )
    pips = estimate_deck_color_pips(deck, card_info=scry.get)
    pause(f"   color pips: {pips}")
    basics = Counter(c.name for c in deck if c.name in BASIC_LANDS)
    pause(f"   basics: {dict(basics)}")

    state = DeckRLState(
        deck=deck,
        pool=dict(pool.available),
        constraints=constraints,
        ratings=ratings,
        iteration=0,
        trajectory=steps_to_dicts(steps),
        meta={"collection": str(args.collection), "color_pips": pips},
    )
    save_checkpoint(args.checkpoint, state)
    pause(f"💾 {args.checkpoint}")

    pause("\n=== Modify loop (refills basics each swap) ===")
    state = run_modify_loop(
        state,
        steps=args.modify_steps,
        checkpoint_path=args.checkpoint,
        card_info=scry.get,
    )
    _print_deck(state.deck)
    pause(
        f"\nResume:\n  PYTHONPATH=src python3 scripts/live_deck_trajectory.py "
        f"--resume {args.checkpoint} --modify-steps 5\n"
    )
    return 0


def _print_deck(deck: list[CardRef]) -> None:
    counts = Counter(c.name for c in deck)
    pause("\n=== Resulting deck ===")
    for n, c in counts.most_common():
        if n not in BASIC_LANDS:
            pause(f"  {c} {n}", 0.01)
    pause("")
    for n in ("Plains", "Island", "Swamp", "Mountain", "Forest"):
        if counts.get(n):
            pause(f"  {counts[n]} {n}", 0.01)


if __name__ == "__main__":
    raise SystemExit(main())
