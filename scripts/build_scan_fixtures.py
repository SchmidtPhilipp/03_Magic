#!/usr/bin/env python3
"""Download Scryfall card art and build scan test fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.vision.fixtures import (  # noqa: E402
    DEFAULT_FIXTURE_NAMES,
    build_card_grid,
    download_scryfall_normals,
)


def main() -> int:
    out_dir = ROOT / "tests" / "fixtures" / "scan"
    cards_dir = out_dir / "cards"
    print(f"Downloading {len(DEFAULT_FIXTURE_NAMES)} cards from Scryfall…")
    paths = download_scryfall_normals(DEFAULT_FIXTURE_NAMES, cards_dir)
    if not paths:
        print("No cards downloaded", file=sys.stderr)
        return 1
    print(f"Got {len(paths)} images")
    build_card_grid([paths[0]], cols=1, rows=1, out_path=out_dir / "single.jpg", gap=0)
    print(f"Wrote {out_dir / 'single.jpg'}")
    nine = paths[:9]
    while len(nine) < 9:
        nine.append(paths[len(nine) % len(paths)])
    build_card_grid(nine, cols=3, rows=3, out_path=out_dir / "binder_3x3.jpg", gap=12)
    print(f"Wrote {out_dir / 'binder_3x3.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
