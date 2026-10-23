"""Manifest load/save and duplicate art_id rejection."""

from __future__ import annotations

from pathlib import Path

import pytest

from magic_optimizer.proxy.manifest import (
    ManifestError,
    assert_manifest_valid,
    load_manifest,
    save_manifest,
    validate_manifest,
)


def _entry(art_id: str, name: str = "Volcanic Island") -> dict:
    return {
        "card_name": name,
        "edition": "PHI",
        "art_id": art_id,
        "source_path": f"originals/PHI/{art_id}.jpg",
    }


def test_duplicate_art_id_returns_error():
    data = {
        "arts": [
            _entry("phi-0001"),
            _entry("phi-0001", name="Bayou"),
        ]
    }
    errors = validate_manifest(data)
    assert errors, "expected duplicate art_id error"
    assert any("duplicate art_id" in e and "phi-0001" in e for e in errors)


def test_duplicate_art_id_raises():
    data = {"arts": [_entry("phi-0001"), _entry("phi-0001")]}
    with pytest.raises(ManifestError, match="duplicate art_id"):
        assert_manifest_valid(data)


def test_missing_required_fields():
    data = {"arts": [{"art_id": "phi-0001", "edition": "PHI"}]}
    errors = validate_manifest(data)
    assert any("card_name" in e for e in errors)
    assert any("source_path" in e for e in errors)


def test_load_save_roundtrip(tmp_path: Path):
    path = tmp_path / "manifest.yaml"
    payload = {"arts": [_entry("phi-0001")]}
    save_manifest(path, payload)
    loaded = load_manifest(path)
    assert loaded["arts"][0]["art_id"] == "phi-0001"
    assert validate_manifest(loaded) == []


def test_empty_manifest_ok():
    assert validate_manifest({"arts": []}) == []
