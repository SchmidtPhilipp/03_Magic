#!/usr/bin/env python3
"""Rebuild the union collection from scan summaries + CSV exports.

Re-run anytime after new scans or CSV updates:

  PYTHONPATH=src python scripts/export_collection_union.py
  PYTHONPATH=src python scripts/export_collection_union.py --no-scryfall   # faster
  PYTHONPATH=src python scripts/export_collection_union.py --no-sqlite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.collection.union_export import (
    build_union,
    sync_union_to_sqlite,
    write_union_outputs,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/collections/union",
        help="Output directory for JSON/CSV",
    )
    ap.add_argument(
        "--no-scryfall",
        action="store_true",
        help="Skip Scryfall enrichment (faster, names only)",
    )
    ap.add_argument(
        "--no-sqlite",
        action="store_true",
        help="Do not sync into mtg_collection.db",
    )
    ap.add_argument(
        "--include-uncertain",
        action="store_true",
        help="Count uncertain scan IDs toward inventory",
    )
    args = ap.parse_args()

    scan_summaries = [
        (
            ROOT
            / "tests/fixtures/scan/real/overlays_batch_new/full_summary.json",
            "scan_batch_new",
        ),
        (
            ROOT
            / "tests/fixtures/scan/real/overlays_batch_verify/full_summary.json",
            "scan_batch_verify",
        ),
    ]
    csv_paths = [
        (
            ROOT / "data/collections/sources/mine/moxfield_main.csv",
            "moxfield_main",
        ),
        (
            ROOT / "data/collections/sources/mine/manabox_fin.csv",
            "manabox_fin",
        ),
        (
            ROOT / "data/collections/sources/mine/manabox_full.csv",
            "manabox_full",
        ),
        (
            ROOT / "data/collections/sources/mine/manabox_hob_2026-08-14.csv",
            "manabox_hob_2026-08-14",
        ),
        (
            ROOT / "data/collections/sources/mine/manabox_grn_sealed_2026-09-11.csv",
            "manabox_grn_sealed_2026-09-11",
        ),
        (
            ROOT / "data/collections/sources/mine/user_confirmed.csv",
            "user_confirmed",
        ),
    ]

    print("Building union…")
    union = build_union(
        scan_summaries=scan_summaries,
        csv_paths=csv_paths,
        include_uncertain=args.include_uncertain,
        resolve_scryfall=not args.no_scryfall,
    )
    paths = write_union_outputs(union, args.out)
    stats = union["stats"]
    print(
        f"unique={stats['unique_cards']} copies={stats['total_copies']} "
        f"(scan_only={stats['scan_only']} csv_only={stats['csv_only']} both={stats['both']})"
    )
    print(f"wrote {paths['json']}")
    print(f"wrote {paths['csv']}")

    if not args.no_sqlite:
        n = sync_union_to_sqlite(union)
        print(f"synced {n} cards → SQLite collection 'Union Collection'")


if __name__ == "__main__":
    main()
