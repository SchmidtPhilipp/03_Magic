# tests/test_name_list_export.py
from pathlib import Path

from magic_optimizer.exporters.name_list import (
    to_arena_text,
    to_copy_paste,
    write_arena_file,
)


def test_to_arena_collapses_counts():
    text = to_arena_text(["Shock", "Shock", "Bolt", "Plains"], title="Test")
    assert "4 " not in text or "Shock" in text
    assert "2 Shock" in text
    assert "1 Bolt" in text
    assert "Test" in text


def test_copy_paste_same_collapse():
    assert "2 Shock" in to_copy_paste(["Shock", "Shock"])


def test_write_arena_file(tmp_path: Path):
    path = write_arena_file(tmp_path / "d.txt", ["Shock", "Shock"])
    assert path.exists()
    assert "2 Shock" in path.read_text(encoding="utf-8")
