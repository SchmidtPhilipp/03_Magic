#!/usr/bin/env python3
"""Match friend inventories against our wishlist + deck gaps.

Drop CSVs into data/collections/sources/friends/ then run:

  PYTHONPATH=src python3 scripts/match_friend_trades.py

Reads:
  - data/collections/wishlist.csv
  - data/collections/keepers_no_trade.csv (never offer these)
  - data/collections/union/union_collection.csv (what we can trade away)
  - data/collections/sources/friends/*.csv

Writes:
  data/collections/trades/trades_<friend>.csv
  data/collections/trades/summary.txt
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRIENDS = ROOT / "data/collections/sources/friends"
UNION = ROOT / "data/collections/union/union_collection.csv"
WISHLIST = ROOT / "data/collections/wishlist.csv"
KEEPERS = ROOT / "data/collections/keepers_no_trade.csv"
OUT = ROOT / "data/collections/trades"

NAME_KEYS = ("card_name", "Name", "name", "Card Name", "card")
QTY_KEYS = ("amount", "Quantity", "quantity", "Qty", "count", "Count")


def _pick(row: dict, keys: tuple[str, ...]) -> str:
    for k in keys:
        if k in row and str(row[k]).strip():
            return str(row[k]).strip()
    return ""


def load_inventory(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = _pick(row, NAME_KEYS)
            if not name:
                continue
            raw = _pick(row, QTY_KEYS) or "1"
            try:
                qty = max(1, int(float(raw)))
            except ValueError:
                qty = 1
            counts[name] += qty
    return counts


def load_wishlist(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_keepers(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as f:
        return {
            row["card_name"]
            for row in csv.DictReader(f)
            if (row.get("status") or "").strip() == "confirmed"
        }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--friends-dir",
        type=Path,
        default=FRIENDS,
        help="Directory of friend CSV inventories",
    )
    args = ap.parse_args()

    if not UNION.is_file():
        raise SystemExit(f"missing union inventory: {UNION}")
    if not WISHLIST.is_file():
        raise SystemExit(f"missing wishlist: {WISHLIST}")

    ours = load_inventory(UNION)
    keepers = load_keepers(KEEPERS) if KEEPERS.is_file() else set()
    wishlist = load_wishlist(WISHLIST)

    friend_files = sorted(
        p
        for p in args.friends_dir.glob("*.csv")
        if p.is_file()
    )
    OUT.mkdir(parents=True, exist_ok=True)

    if not friend_files:
        (OUT / "summary.txt").write_text(
            "No friend CSVs yet.\n"
            f"Drop files into {FRIENDS.relative_to(ROOT)} and re-run.\n",
            encoding="utf-8",
        )
        print(f"no friend CSVs in {args.friends_dir}")
        print(f"wrote {OUT / 'summary.txt'}")
        return 0

    summary: list[str] = ["Trade match summary", ""]
    for path in friend_files:
        friend = load_inventory(path)
        stem = path.stem
        rows_out: list[dict] = []
        hits = 0
        for w in wishlist:
            name = w["card_name"]
            have_us = int(w.get("have") or ours.get(name, 0))
            want = int(float(w.get("want_qty") or 1))
            need = max(0, want - have_us)
            they = friend.get(name, 0)
            if need <= 0 or they <= 0:
                continue
            hits += 1
            rows_out.append(
                {
                    "card_name": name,
                    "priority": w.get("priority", ""),
                    "for_deck": w.get("for_deck", ""),
                    "we_need": need,
                    "they_have": they,
                    "trade_qty": min(need, they),
                    "reason": w.get("reason", ""),
                }
            )

        # What we could offer (owned, not keepers, they might want later — list surplus commons later)
        offerable = sorted(
            (
                n
                for n, q in ours.items()
                if q > 0 and n not in keepers
            ),
            key=str,
        )

        out_csv = OUT / f"trades_{stem}.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            fields = [
                "card_name",
                "priority",
                "for_deck",
                "we_need",
                "they_have",
                "trade_qty",
                "reason",
            ]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            # high priority first
            rows_out.sort(
                key=lambda r: (
                    {"high": 0, "med": 1, "low": 2}.get(r["priority"], 9),
                    r["card_name"],
                )
            )
            for row in rows_out:
                w.writerow(row)

        summary.append(f"## {stem}")
        summary.append(f"wishlist hits: {hits}")
        summary.append(f"report: {out_csv.relative_to(ROOT)}")
        if rows_out:
            summary.append("top asks:")
            for row in rows_out[:10]:
                summary.append(
                    f"  - {row['trade_qty']} {row['card_name']} "
                    f"[{row['priority']}] for {row['for_deck']}"
                )
        else:
            summary.append("  (no wishlist overlaps)")
        summary.append(
            f"our offerable non-keepers (count): {len(offerable)}"
        )
        summary.append("")

    (OUT / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"matched {len(friend_files)} friend file(s) → {OUT}")
    print((OUT / "summary.txt").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
