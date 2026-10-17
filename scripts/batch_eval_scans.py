#!/usr/bin/env python3
"""Batch-eval current pipeline on binder scans (detect + optional ID)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_IN = ROOT / "tests/fixtures/scan/real/batch_new"
DEFAULT_OUT = ROOT / "tests/fixtures/scan/real/overlays_batch_new"


def _parse_dirs(argv: list[str]) -> tuple[Path, Path, bool]:
    only_detect = "--detect-only" in argv
    in_dir, out_dir = DEFAULT_IN, DEFAULT_OUT
    if "--in" in argv:
        in_dir = Path(argv[argv.index("--in") + 1])
    if "--out" in argv:
        out_dir = Path(argv[argv.index("--out") + 1])
    out_dir.mkdir(parents=True, exist_ok=True)
    return in_dir, out_dir, only_detect


def main() -> None:
    from magic_optimizer.vision.binder_grid import detect_binder_slots
    from magic_optimizer.vision.detect import detect_card_regions
    from magic_optimizer.vision.overlay import render_overlay
    from magic_optimizer.vision.yolo import detect_with_yolo
    import magic_optimizer.vision.identify as identify_mod
    import magic_optimizer.vision.yolo as yolo_mod

    identify_mod._MILO = None
    identify_mod._MILO_TRIED = False
    yolo_mod._model = None

    in_dir, out_dir, only_detect = _parse_dirs(sys.argv)
    files = sorted(in_dir.glob("*.png"))
    print(f"files: {len(files)}  mode={'detect-only' if only_detect else 'full'}")
    print(f"in={in_dir}  out={out_dir}")

    summary = []
    t0 = time.time()
    for path in files:
        t1 = time.time()
        if only_detect:
            grid = detect_binder_slots(str(path))
            yolo = detect_with_yolo(str(path)) if not grid else []
            dets = grid or yolo
            named = [
                {
                    **d,
                    "detected_name": f"{d.get('source','?')}:{float(d.get('confidence') or 0):.2f}",
                    "status": "accepted",
                }
                for d in dets
            ]
        else:
            dets = detect_card_regions(str(path))
            named = []
            for d in dets:
                label = d.get("detected_name") or "?"
                if d.get("uncertain"):
                    label = f"? {label}"
                named.append(
                    {
                        **d,
                        "detected_name": label,
                        "status": "pending" if d.get("uncertain") else "accepted",
                    }
                )

        out = out_dir / f"{path.stem}.jpg"
        render_overlay(str(path), named, str(out))
        unc = sum(1 for d in dets if d.get("uncertain"))
        srcs: dict[str, int] = {}
        for d in dets:
            s = str(d.get("source") or "?")
            srcs[s] = srcs.get(s, 0) + 1
        row = {
            "file": path.name,
            "n": len(dets),
            "uncertain": unc,
            "sources": srcs,
            "names": [d.get("detected_name") for d in named],
            "seconds": round(time.time() - t1, 1),
            "overlay": str(out),
        }
        summary.append(row)
        print(
            f"{path.name}: n={len(dets)} unc={unc} src={srcs} ({row['seconds']}s)"
        )
        if not only_detect:
            for nm in row["names"]:
                print(f"    {nm}")

    payload = {
        "mode": "detect-only" if only_detect else "full",
        "n_images": len(files),
        "total_dets": sum(r["n"] for r in summary),
        "total_uncertain": sum(r["uncertain"] for r in summary),
        "elapsed_s": round(time.time() - t0, 1),
        "in_dir": str(in_dir),
        "out_dir": str(out_dir),
        "per_image": summary,
    }
    out_json = out_dir / ("detect_summary.json" if only_detect else "full_summary.json")
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"\nTOTAL images={len(files)} dets={payload['total_dets']} "
        f"unc={payload['total_uncertain']} elapsed={payload['elapsed_s']}s"
    )
    if payload["total_dets"]:
        auto = payload["total_dets"] - payload["total_uncertain"]
        print(
            f"auto-accept={100 * auto / payload['total_dets']:.2f}%  "
            f"uncertain={100 * payload['total_uncertain'] / payload['total_dets']:.2f}%"
        )
    print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
