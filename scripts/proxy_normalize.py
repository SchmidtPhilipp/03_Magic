#!/usr/bin/env python3
"""Normalize proxy originals to 488×680 into data/proxy/normalized/.

  PYTHONPATH=src python scripts/proxy_normalize.py
  PYTHONPATH=src python scripts/proxy_normalize.py --art-id phi-0001
  PYTHONPATH=src python scripts/proxy_normalize.py --all

Never mutates files under originals/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.proxy.config import load_config
from magic_optimizer.proxy.manifest import load_manifest, save_manifest
from magic_optimizer.proxy.normalize import normalize_image


def _resolve(root: Path, rel: str) -> Path:
    path = Path(rel)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def normalize_entry(entry: dict, *, cfg) -> Path:
    """Normalize one manifest art; update entry in place; return dest path."""
    source_rel = entry.get("source_path")
    if not source_rel:
        raise ValueError(f"art_id={entry.get('art_id')}: missing source_path")

    source = _resolve(cfg.root, str(source_rel))
    if not source.is_file():
        raise FileNotFoundError(f"Missing original: {source}")

    # Mirror originals/… under normalized/
    try:
        rel = source.relative_to(cfg.resolve_path("originals"))
    except ValueError:
        edition = str(entry.get("edition") or "PHI").upper()
        rel = Path(edition) / source.name

    dest = cfg.resolve_path("normalized") / rel
    # Prefer .jpg for normalized outputs
    if dest.suffix.lower() not in {".jpg", ".jpeg"}:
        dest = dest.with_suffix(".jpg")

    normalize_image(
        source,
        dest,
        width=cfg.reference_width,
        height=cfg.reference_height,
    )

    entry["normalized_path"] = dest.relative_to(cfg.root).as_posix()
    entry["pixel_width"] = cfg.reference_width
    entry["pixel_height"] = cfg.reference_height
    if entry.get("status") in (None, "imported"):
        entry["status"] = "normalized"
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--art-id", action="append", default=[], help="Normalize this art_id (repeatable)")
    ap.add_argument("--all", action="store_true", help="Normalize every manifest art")
    ap.add_argument("--config", type=Path, default=None)
    args = ap.parse_args()

    if not args.all and not args.art_id:
        args.all = True

    cfg = load_config(args.config)
    manifest_path = cfg.resolve_path("manifest")
    data = load_manifest(manifest_path)
    arts = list(data.get("arts") or [])
    if not arts:
        print("No arts in manifest.", file=sys.stderr)
        raise SystemExit(0)

    selected_ids = {a.strip() for a in args.art_id} if args.art_id else None
    done = 0
    for entry in arts:
        if not isinstance(entry, dict):
            continue
        art_id = entry.get("art_id")
        if selected_ids is not None and art_id not in selected_ids:
            continue
        dest = normalize_entry(entry, cfg=cfg)
        print(f"Normalized {art_id} → {dest.relative_to(cfg.root)}")
        done += 1

    if selected_ids is not None:
        missing = selected_ids - {
            e.get("art_id") for e in arts if isinstance(e, dict)
        }
        if missing:
            print(f"Unknown art_id(s): {', '.join(sorted(missing))}", file=sys.stderr)
            raise SystemExit(1)

    if done == 0:
        print("Nothing to normalize.", file=sys.stderr)
        raise SystemExit(1)

    data["arts"] = arts
    save_manifest(manifest_path, data)


if __name__ == "__main__":
    main()
