#!/usr/bin/env python3
"""Validate proxy manifest + files; exit non-zero on any error.

  PYTHONPATH=src python scripts/proxy_validate.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.proxy.config import load_config
from magic_optimizer.proxy.manifest import load_manifest
from magic_optimizer.proxy.validate import validate_proxy


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument(
        "--no-normalized",
        action="store_true",
        help="Skip dimension checks on normalized_path",
    )
    args = ap.parse_args()

    cfg = load_config(args.config)
    manifest_path = cfg.resolve_path("manifest")
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        raise SystemExit(1)

    data = load_manifest(manifest_path)
    issues = validate_proxy(
        data,
        config=cfg,
        check_normalized=not args.no_normalized,
    )

    if not issues:
        n = len(data.get("arts") or [])
        print(f"OK — {n} art(s), no issues.")
        raise SystemExit(0)

    for issue in issues:
        loc = issue.art_id or issue.path or ""
        prefix = f"[{issue.code}]"
        if loc:
            print(f"{prefix} {issue.message} ({loc})", file=sys.stderr)
        else:
            print(f"{prefix} {issue.message}", file=sys.stderr)

    print(f"{len(issues)} issue(s).", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
