#!/usr/bin/env python3
"""Render S3-wired production overlays for real binder fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.vision.detect import detect_card_regions
from magic_optimizer.vision.overlay import render_overlay
import magic_optimizer.vision.yolo as yolo_mod
import magic_optimizer.vision.identify as identify_mod

REAL = ROOT / "tests/fixtures/scan/real"
OUT = REAL / "overlays_s3_prod"
PHOTOS = [
    "binder_partial_4cards.png",
    "binder_rotated_glare.png",
    "binder_red_glare.png",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # fresh engines
    yolo_mod._model = None
    identify_mod._MILO = None
    identify_mod._MILO_TRIED = False

    for fname in PHOTOS:
        path = REAL / fname
        print(f"detect+identify {fname}…")
        dets = detect_card_regions(str(path))
        named = []
        for d in dets:
            label = d.get("detected_name") or "?"
            if d.get("uncertain"):
                label = f"? {label}"
            status = "pending" if d.get("uncertain") else "accepted"
            named.append({**d, "detected_name": label, "status": status})
            print(
                f"  {label:40} conf={float(d.get('confidence') or 0):.3f} "
                f"src={d.get('id_source')} unc={d.get('uncertain')}"
            )
        out = OUT / f"{path.stem}_s3.jpg"
        render_overlay(str(path), named, str(out))
        print(f"  → {out}\n")


if __name__ == "__main__":
    main()
