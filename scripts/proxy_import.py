#!/usr/bin/env python3
"""Copy a card image into data/proxy/originals/ and append a manifest entry.

  PYTHONPATH=src python scripts/proxy_import.py \\
    --source /path/to/art.jpg \\
    --card-name "Volcanic Island" \\
    --art-id phi-0001 \\
    --edition PHI

Refuses to overwrite an existing original unless ``--force``.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.proxy.config import load_config
from magic_optimizer.proxy.manifest import load_manifest, save_manifest, validate_manifest


def slugify_card_name(name: str) -> str:
    """Scryfall-style slug: lowercase, non-alnum → hyphen, collapsed."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def default_filename(
    *,
    card_name: str,
    edition: str,
    art_id: str,
    suffix: str,
) -> str:
    """``{slug}__{edition}-{nnnn}{suffix}`` e.g. ``volcanic-island__phi-0001.jpg``.

    If ``art_id`` already contains ``__`` (full id like ``badlands__phi-0002``),
    use it as the basename so imports are not double-prefixed.
    If ``art_id`` is only ``phi-0002`` / ``0002``, build ``{slug}__phi-0002``.
    """
    slug = slugify_card_name(card_name)
    ed = edition.strip().lower()
    token = art_id.strip()
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    if "__" in token:
        base = token
        if base.lower().endswith(ext.lower()):
            return base
        return f"{base}{ext}"
    if not token.lower().startswith(f"{ed}-"):
        token = f"{ed}-{token}"
    return f"{slug}__{token}{ext}"


def import_art(
    *,
    source: Path,
    card_name: str,
    art_id: str,
    edition: str = "PHI",
    collector_number: str | None = None,
    force: bool = False,
    config_path: Path | None = None,
) -> dict:
    """Copy source → originals/, append manifest entry. Returns the new entry."""
    cfg = load_config(config_path)
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source image not found: {source}")

    originals = cfg.resolve_path("originals")
    dest_name = default_filename(
        card_name=card_name,
        edition=edition,
        art_id=art_id,
        suffix=source.suffix.lower() or ".jpg",
    )
    dest = originals / edition.strip().upper() / dest_name
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite existing original (use --force): {dest}"
        )

    shutil.copy2(source, dest)

    manifest_path = cfg.resolve_path("manifest")
    if not manifest_path.is_file():
        data = {"arts": []}
    else:
        data = load_manifest(manifest_path)

    rel_source = dest.relative_to(cfg.root).as_posix()
    # Replace existing art_id entry when --force
    arts = list(data.get("arts") or [])
    arts = [e for e in arts if not (isinstance(e, dict) and e.get("art_id") == art_id)]

    cn = collector_number
    if cn is None:
        # Derive from art_id trailing digits if present
        m = re.search(r"(\d+)$", art_id.strip())
        cn = m.group(1) if m else None

    entry = {
        "card_name": card_name,
        "edition": edition.strip().upper(),
        "art_id": art_id.strip(),
        "source_path": rel_source,
        "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "imported",
    }
    if cn is not None:
        entry["collector_number"] = str(cn)

    arts.append(entry)
    data["arts"] = arts
    errors = validate_manifest(data)
    if errors:
        raise SystemExit(f"Manifest invalid after import: {'; '.join(errors)}")
    save_manifest(manifest_path, data)
    return entry


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True, help="Image file to copy")
    ap.add_argument("--card-name", required=True, help='e.g. "Volcanic Island"')
    ap.add_argument("--art-id", required=True, help="Unique id, e.g. phi-0001")
    ap.add_argument("--edition", default="PHI")
    ap.add_argument("--collector-number", default=None)
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing original and replace manifest entry",
    )
    ap.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to config.yaml",
    )
    args = ap.parse_args()

    try:
        entry = import_art(
            source=args.source,
            card_name=args.card_name,
            art_id=args.art_id,
            edition=args.edition,
            collector_number=args.collector_number,
            force=args.force,
            config_path=args.config,
        )
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Imported {entry['art_id']} → {entry['source_path']}")


if __name__ == "__main__":
    main()
