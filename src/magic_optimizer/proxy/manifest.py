"""Load, save, and validate the proxy arts manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

import yaml

REQUIRED_FIELDS = ("card_name", "edition", "art_id", "source_path")


class ManifestError(ValueError):
    """Manifest structure or uniqueness validation failed."""


def load_manifest(path: Path | str) -> dict[str, Any]:
    """Load manifest YAML; ensure top-level ``arts`` list exists."""
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        data = {"arts": []}
    if not isinstance(data, dict):
        raise ManifestError(f"Manifest root must be a mapping: {path}")
    arts = data.get("arts")
    if arts is None:
        data["arts"] = []
    elif not isinstance(arts, list):
        raise ManifestError(f"Manifest 'arts' must be a list: {path}")
    return data


def save_manifest(path: Path | str, data: Mapping[str, Any]) -> None:
    """Write manifest YAML (creates parent dirs if needed)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: MutableMapping[str, Any] = dict(data)
    if "arts" not in payload:
        payload["arts"] = []
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False, allow_unicode=True)


def validate_manifest(data: Mapping[str, Any]) -> list[str]:
    """Return human-readable errors; empty list means OK.

    Checks required fields and unique ``art_id`` values.
    """
    errors: list[str] = []
    arts = data.get("arts")
    if arts is None:
        return ["missing 'arts' list"]
    if not isinstance(arts, list):
        return ["'arts' must be a list"]

    seen: dict[str, int] = {}
    for idx, entry in enumerate(arts):
        if not isinstance(entry, Mapping):
            errors.append(f"arts[{idx}]: entry must be a mapping")
            continue
        for field in REQUIRED_FIELDS:
            value = entry.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"arts[{idx}]: missing required field '{field}'")
        art_id = entry.get("art_id")
        if art_id is not None and str(art_id).strip():
            key = str(art_id)
            if key in seen:
                errors.append(
                    f"duplicate art_id '{key}' at arts[{idx}] "
                    f"(first at arts[{seen[key]}])"
                )
            else:
                seen[key] = idx
    return errors


def assert_manifest_valid(data: Mapping[str, Any]) -> None:
    """Raise ``ManifestError`` if validation fails."""
    errors = validate_manifest(data)
    if errors:
        raise ManifestError("; ".join(errors))


def iter_arts(data: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    """Return the arts list (empty if missing)."""
    arts = data.get("arts") or []
    if not isinstance(arts, list):
        raise ManifestError("'arts' must be a list")
    return arts
