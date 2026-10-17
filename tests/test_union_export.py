"""Tests for union collection export."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from magic_optimizer.collection.union_export import (
    build_union,
    write_union_outputs,
)


def test_union_max_across_overlapping_csv_sources(tmp_path: Path):
    csv_a = tmp_path / "a.csv"
    csv_a.write_text(
        "amount,card_name,set_code,collector_number,language\n"
        "1,Lightning Bolt,LEA,161,en\n",
        encoding="utf-8",
    )
    csv_b = tmp_path / "b.csv"
    csv_b.write_text(
        "Name,Set code,Collector number,Quantity,Scryfall ID,Language\n"
        "Lightning Bolt,M21,161,3,abc,en\n",
        encoding="utf-8",
    )
    with patch(
        "magic_optimizer.collection.union_export.lookup_card_name",
        return_value=None,
    ):
        union = build_union(
            scan_summaries=[],
            csv_paths=[(csv_a, "csv_a"), (csv_b, "csv_b")],
            resolve_scryfall=False,
            scryfall_sleep=0,
        )
    bolt = union["cards"][0]
    assert bolt["card_name"] == "Lightning Bolt"
    # max(1, 3) not 4
    assert bolt["amount"] == 3
    assert bolt["csv_amount"] == 3


def test_union_max_of_scan_and_csv(tmp_path: Path):
    summary = {
        "per_image": [
            {
                "file": "a.png",
                "names": ["Lightning Bolt", "Lightning Bolt", "? Blank Card"],
            }
        ]
    }
    scan = tmp_path / "summary.json"
    scan.write_text(json.dumps(summary), encoding="utf-8")

    csv_file = tmp_path / "col.csv"
    csv_file.write_text(
        "amount,card_name,set_code,collector_number,language\n"
        "4,Lightning Bolt,LEA,161,en\n"
        "1,Counterspell,LEA,54,en\n",
        encoding="utf-8",
    )

    with patch(
        "magic_optimizer.collection.union_export.lookup_card_name",
        side_effect=lambda n: {
            "card_name": n,
            "scryfall_id": f"id-{n}",
            "set_code": "LEA",
            "collector_number": "1",
        },
    ):
        union = build_union(
            scan_summaries=[(scan, "scan_a")],
            csv_paths=[(csv_file, "csv_a")],
            resolve_scryfall=True,
            scryfall_sleep=0,
        )

    by_name = {c["card_name"]: c for c in union["cards"]}
    # scan=2, csv=4 → max=4
    assert by_name["Lightning Bolt"]["amount"] == 4
    assert by_name["Lightning Bolt"]["scan_hits"] == 2
    assert by_name["Lightning Bolt"]["csv_amount"] == 4
    # csv only
    assert by_name["Counterspell"]["amount"] == 1
    # junk blank skipped
    assert "Blank Card" not in by_name

    out = write_union_outputs(union, tmp_path / "out")
    assert out["json"].exists()
    assert out["csv"].exists()
