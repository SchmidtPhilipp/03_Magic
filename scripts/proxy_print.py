#!/usr/bin/env python3
"""Build an A4 proxy PDF from a simple quantity list.

Qty file lines (blank/# comments ignored)::

    4 Volcanic Island
    1 phi-0001

  PYTHONPATH=src python scripts/proxy_print.py --list deck.txt
  PYTHONPATH=src python scripts/proxy_print.py --list deck.txt --out prints/run.pdf

Print the PDF at **100% / actual size** (not fit-to-page).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.proxy.config import load_config
from magic_optimizer.proxy.layout import layout_from_config
from magic_optimizer.proxy.manifest import load_manifest
from magic_optimizer.proxy.pdf import write_proxy_pdf

_QTY_RE = re.compile(
    r"^\s*(\d+)\s+(.+?)\s*$"
)


def parse_qty_list(text: str) -> list[tuple[int, str]]:
    """Parse ``N NameOrArtId`` lines → list of (qty, key)."""
    rows: list[tuple[int, str]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _QTY_RE.match(line)
        if not m:
            raise ValueError(f"line {lineno}: expected 'N NameOrArtId', got {raw!r}")
        qty = int(m.group(1))
        if qty < 1:
            raise ValueError(f"line {lineno}: quantity must be >= 1")
        rows.append((qty, m.group(2).strip()))
    return rows


def _resolve_path(root: Path, rel: str | None) -> Path | None:
    if not rel:
        return None
    path = Path(str(rel))
    if path.is_absolute():
        return path if path.is_file() else None
    full = (root / path).resolve()
    return full if full.is_file() else None


def find_art(
    arts: Sequence[Mapping[str, Any]],
    key: str,
    *,
    edition: str | None = "PHI",
) -> Mapping[str, Any]:
    """Resolve a qty-list key to a manifest entry (art_id, then card_name)."""
    key_l = key.strip().lower()

    for entry in arts:
        art_id = str(entry.get("art_id") or "").strip()
        if art_id.lower() == key_l:
            return entry

    matches = [
        e
        for e in arts
        if str(e.get("card_name") or "").strip().lower() == key_l
    ]
    if edition:
        ed = edition.strip().upper()
        preferred = [
            e for e in matches if str(e.get("edition") or "").upper() == ed
        ]
        if preferred:
            matches = preferred
    # Prefer normalized / print_ready
    def rank(e: Mapping[str, Any]) -> tuple[int, int]:
        status = str(e.get("status") or "")
        has_norm = 1 if e.get("normalized_path") else 0
        status_score = 2 if status == "print_ready" else (1 if status == "normalized" else 0)
        return (has_norm, status_score)

    if not matches:
        raise KeyError(f"No manifest art for {key!r}")
    matches = sorted(matches, key=rank, reverse=True)
    return matches[0]


def expand_images(
    qty_rows: Sequence[tuple[int, str]],
    *,
    arts: Sequence[Mapping[str, Any]],
    root: Path,
    edition: str | None = "PHI",
) -> list[Path]:
    """Expand qty list to image paths (normalized preferred, else source)."""
    paths: list[Path] = []
    for qty, key in qty_rows:
        entry = find_art(arts, key, edition=edition)
        norm = _resolve_path(root, entry.get("normalized_path"))
        src = _resolve_path(root, entry.get("source_path"))
        image = norm or src
        if image is None:
            raise FileNotFoundError(
                f"No image file for art_id={entry.get('art_id')} "
                f"(normalized_path / source_path missing on disk)"
            )
        paths.extend([image] * qty)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", type=Path, required=True, help="Qty list file")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output PDF (default: data/proxy/prints/proxy-YYYYMMDD-HHMMSS.pdf)",
    )
    ap.add_argument("--orientation", choices=("portrait", "landscape"), default=None)
    ap.add_argument("--edition", default="PHI", help="Preferred edition for name match")
    ap.add_argument("--config", type=Path, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    qty_text = args.list.read_text(encoding="utf-8")
    try:
        rows = parse_qty_list(qty_text)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    if not rows:
        print("Qty list is empty.", file=sys.stderr)
        raise SystemExit(1)

    data = load_manifest(cfg.resolve_path("manifest"))
    arts = [e for e in (data.get("arts") or []) if isinstance(e, dict)]

    try:
        images = expand_images(
            rows, arts=arts, root=cfg.root, edition=args.edition
        )
    except (KeyError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    layout = layout_from_config(cfg, orientation=args.orientation)
    out = args.out
    if out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out = cfg.resolve_path("prints") / f"proxy-{stamp}.pdf"
    else:
        out = Path(out)
        if not out.is_absolute():
            # Relative paths land under prints/ unless they already include it
            out = (cfg.resolve_path("prints") / out.name) if out.parent == Path(".") else out

    dest = write_proxy_pdf(
        images,
        out,
        layout=layout,
        corner_radius_mm=cfg.corner_radius_mm,
    )
    pages = (len(images) + layout.slots_per_page - 1) // layout.slots_per_page
    print(
        f"Wrote {dest} ({len(images)} cards, {pages} page(s), "
        f"{layout.cols}×{layout.rows} grid, "
        f"card {layout.card_width_mm}×{layout.card_height_mm} mm, "
        f"gap {layout.gap_mm} mm, corner r={cfg.corner_radius_mm} mm)"
    )
    print("Print at 100% / actual size — do not use fit-to-page.")


if __name__ == "__main__":
    main()
