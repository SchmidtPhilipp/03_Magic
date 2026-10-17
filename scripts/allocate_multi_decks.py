#!/usr/bin/env python3
"""Allocate several 60-card decks from one inventory without over-drawing copies.

Usage:
  PYTHONPATH=src python3 scripts/allocate_multi_decks.py \\
    --inventory data/collections/union/union_collection.csv \\
    --decks-dir data/decks/active \\
    --out-dir data/decks/allocated

Rules:
  - Decks may share card *names*, but total assigned copies ≤ owned.
  - Priority order = file order (or --priority list).
  - Basics are unlimited.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

BASIC = frozenset({"Plains", "Island", "Swamp", "Mountain", "Forest"})


def load_inventory(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("card_name") or row.get("Name") or "").strip()
            if not name:
                continue
            raw = row.get("amount") or row.get("Quantity") or 1
            counts[name] += max(1, int(float(raw)))
    return counts


def parse_decklist(path: Path) -> Counter[str]:
    """Accept '4 Llanowar Elves' or '1x Card Name' lines."""
    out: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\d+)\s*[xX]?\s+(.+)$", line)
        if not m:
            continue
        out[m.group(2).strip()] += int(m.group(1))
    return out


def allocate(
    inventory: Counter[str],
    wanted: dict[str, Counter[str]],
    *,
    priority: list[str],
) -> tuple[dict[str, Counter[str]], dict[str, Counter[str]], Counter[str]]:
    """Return (allocated, shortfalls, remaining)."""
    remaining = Counter(inventory)
    allocated: dict[str, Counter[str]] = {k: Counter() for k in priority}
    shortfalls: dict[str, Counter[str]] = {k: Counter() for k in priority}

    for deck_id in priority:
        need = wanted[deck_id]
        for name, qty in sorted(need.items(), key=lambda x: x[0]):
            if name in BASIC:
                allocated[deck_id][name] = qty
                continue
            take = min(qty, remaining[name])
            if take:
                allocated[deck_id][name] = take
                remaining[name] -= take
            miss = qty - take
            if miss:
                shortfalls[deck_id][name] = miss
    return allocated, shortfalls, remaining


def write_deck(path: Path, counts: Counter[str]) -> None:
    lines = [f"{q} {n}" for n, q in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--inventory",
        default="data/collections/union/union_collection.csv",
    )
    p.add_argument("--decks-dir", default="data/decks/active")
    p.add_argument("--out-dir", default="data/decks/allocated")
    p.add_argument(
        "--priority",
        default="",
        help="Comma-separated deck file stems; default = alphabetical",
    )
    args = p.parse_args(argv)

    decks_dir = Path(args.decks_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory = load_inventory(Path(args.inventory))
    files = sorted(decks_dir.glob("*.txt"))
    # ignore nested allocated if scanning parent
    files = [f for f in files if f.parent == decks_dir]
    wanted = {f.stem: parse_decklist(f) for f in files}
    if not wanted:
        print(f"no decklists in {decks_dir}")
        return 1

    if args.priority.strip():
        priority = [s.strip() for s in args.priority.split(",") if s.strip()]
        for stem in priority:
            if stem not in wanted:
                raise SystemExit(f"unknown deck in --priority: {stem}")
        # append any missing at end
        for stem in wanted:
            if stem not in priority:
                priority.append(stem)
    else:
        # Prefer flagship / high-power first
        preferred = [
            "temur-ureni-dragons",
            "mono-g-ramp-titan-craterhoof",
            "br-griselbrand-reanimator-ish",
            "elves-into-craterhoof",
            "ur-niv-mizzet",
            "5c-omnath-goodstuff",
        ]
        priority = [s for s in preferred if s in wanted]
        priority += sorted(s for s in wanted if s not in priority)

    allocated, shortfalls, remaining = allocate(inventory, wanted, priority=priority)

    report_lines = ["# multi-deck allocation", f"priority: {', '.join(priority)}", ""]
    for stem in priority:
        write_deck(out_dir / f"{stem}.txt", allocated[stem])
        miss = shortfalls[stem]
        total = sum(allocated[stem].values())
        report_lines.append(f"## {stem}  ({total} cards assigned)")
        if miss:
            report_lines.append("shortfall:")
            for n, q in sorted(miss.items(), key=lambda x: (-x[1], x[0])):
                report_lines.append(f"  - need {q} more {n} (owned left after higher-prio: check wishlist)")
        else:
            report_lines.append("shortfall: none")
        report_lines.append("")

    # cards still free for new decks / trade consideration (excluding keepers handled elsewhere)
    leftovers = [(n, q) for n, q in remaining.items() if q > 0 and n not in BASIC]
    leftovers.sort(key=lambda x: (-x[1], x[0]))
    report_lines.append(f"## remaining inventory ({sum(q for _, q in leftovers)} nonbasic copies)")
    for n, q in leftovers[:40]:
        report_lines.append(f"  {q} {n}")
    if len(leftovers) > 40:
        report_lines.append(f"  ... +{len(leftovers) - 40} more")

    (out_dir / "ALLOCATION.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"wrote {len(priority)} decks → {out_dir}")
    short_n = sum(1 for s in shortfalls.values() if s)
    print(f"decks with shortfalls: {short_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
