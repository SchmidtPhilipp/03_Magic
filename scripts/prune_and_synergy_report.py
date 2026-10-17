#!/usr/bin/env python3
"""Report strict supersessions and optional synergy edges for a collection.

Live Scryfall is used only when facts are missing from --facts-cache.
Offline tests should inject facts via --facts-json instead.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.deck_picker.types import CardPool
from magic_optimizer.pool_prune.dominance import prune_superseded
from magic_optimizer.pool_prune.facts import CardFacts, CardFactsStore
from magic_optimizer.synergy.learn import learn_synergy_from_jsonl


def _pool_from_csv(path: Path) -> CardPool:
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("card_name") or "").strip().strip('"')
            if not name:
                continue
            try:
                qty = int(row.get("amount") or 1)
            except ValueError:
                qty = 1
            counts[name] += max(1, qty)
    return CardPool({n: min(4, q) for n, q in counts.items()})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collection-csv",
        default="data/collections/collection_278079_69871_1751833200.csv",
    )
    parser.add_argument("--facts-cache", default="runs/card_facts_cache.json")
    parser.add_argument(
        "--facts-json",
        default="",
        help="Optional precomputed {name: CardFacts dict} — skips Scryfall",
    )
    parser.add_argument("--synergy-jsonl", default="")
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args(argv)

    pool = _pool_from_csv(Path(args.collection_csv))
    if args.facts_json:
        raw = json.loads(Path(args.facts_json).read_text(encoding="utf-8"))
        facts = {str(k): CardFacts.from_dict(v) for k, v in raw.items()}
    else:
        store = CardFactsStore(cache_path=args.facts_cache)
        facts = store.get_many(pool.available.keys())

    pruned, report = prune_superseded(pool, facts)
    print(
        json.dumps(
            {
                "pool_original": report["original_pool_size"],
                "pool_kept": report["kept_pool_size"],
                "dropped_count": report["dropped_count"],
                "supersessions_sample": report["supersessions"][: max(0, args.top)],
                "facts_loaded": len(facts),
            },
            indent=2,
        )
    )

    if args.synergy_jsonl:
        graph = learn_synergy_from_jsonl(args.synergy_jsonl)
        edges = [
            {"a": a, "b": b, "weight": w} for a, b, w in graph.top_edges(args.top)
        ]
        print(json.dumps({"synergy_edges": len(graph), "top_edges": edges}, indent=2))

    print(
        json.dumps({"pruned_unique": len(pruned.available)}, indent=2),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
