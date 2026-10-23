"""Load proxy pipeline config and resolve paths under data/proxy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

# Repo root = parents[3] from this file: .../src/magic_optimizer/proxy/config.py
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_PROXY_ROOT = _DEFAULT_REPO_ROOT / "data" / "proxy"
_DEFAULT_CONFIG_NAME = "config.yaml"


@dataclass(frozen=True)
class ProxyConfig:
    """Resolved proxy pipeline settings."""

    reference_width: int
    reference_height: int
    card_width_mm: float
    card_height_mm: float
    page: Mapping[str, Any]
    margins_mm: Mapping[str, float]
    gap_mm: float
    center_grid: bool
    corner_radius_mm: float
    paths: Mapping[str, str]
    root: Path
    raw: Mapping[str, Any]

    def resolve_path(self, key_or_relative: str) -> Path:
        """Resolve a paths.* key or a relative path against ``root`` (data/proxy)."""
        relative = self.paths.get(key_or_relative, key_or_relative)
        path = Path(relative)
        if path.is_absolute():
            return path
        return (self.root / path).resolve()


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward for a directory that contains ``data/proxy`` or ``src/magic_optimizer``."""
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "data" / "proxy").is_dir():
            return candidate
        if (candidate / "src" / "magic_optimizer").is_dir():
            return candidate
    return _DEFAULT_REPO_ROOT


def load_config(
    path: Path | str | None = None,
    *,
    repo_root: Path | str | None = None,
    proxy_root: Path | str | None = None,
) -> ProxyConfig:
    """Load ``config.yaml`` and resolve paths relative to ``data/proxy``.

    Resolution order for the config file:
    1. Explicit ``path``
    2. ``proxy_root / config.yaml``
    3. ``repo_root / data/proxy / config.yaml`` (repo_root auto-detected if omitted)
    """
    if path is not None:
        config_path = Path(path).resolve()
        root = proxy_root if proxy_root is not None else config_path.parent
        root = Path(root).resolve()
    elif proxy_root is not None:
        root = Path(proxy_root).resolve()
        config_path = root / _DEFAULT_CONFIG_NAME
    else:
        repo = Path(repo_root).resolve() if repo_root is not None else find_repo_root()
        root = (repo / "data" / "proxy").resolve()
        config_path = root / _DEFAULT_CONFIG_NAME

    if not config_path.is_file():
        raise FileNotFoundError(f"Proxy config not found: {config_path}")

    with config_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Proxy config must be a mapping: {config_path}")

    paths = dict(raw.get("paths") or {})
    margins = {k: float(v) for k, v in dict(raw.get("margins_mm") or {}).items()}
    page = dict(raw.get("page") or {})

    return ProxyConfig(
        reference_width=int(raw["reference_width"]),
        reference_height=int(raw["reference_height"]),
        card_width_mm=float(raw["card_width_mm"]),
        card_height_mm=float(raw["card_height_mm"]),
        page=page,
        margins_mm=margins,
        gap_mm=float(raw.get("gap_mm", 0)),
        center_grid=bool(raw.get("center_grid", True)),
        corner_radius_mm=float(raw.get("corner_radius_mm", 2.5)),
        paths=paths,
        root=root,
        raw=raw,
    )
