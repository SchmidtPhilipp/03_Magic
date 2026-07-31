"""Tests for scan fixture image composition."""

from pathlib import Path

from PIL import Image

from magic_optimizer.vision.fixtures import build_card_grid


def test_build_card_grid_3x3(tmp_path: Path):
    cards = []
    for i in range(9):
        p = tmp_path / f"c{i}.jpg"
        Image.new("RGB", (100, 140), (i * 20, 40, 80)).save(p)
        cards.append(p)
    out = tmp_path / "grid.jpg"
    build_card_grid(cards, cols=3, rows=3, out_path=out, gap=4)
    img = Image.open(out)
    assert img.size == (100 * 3 + 4 * 4, 140 * 3 + 4 * 4)


def test_build_card_grid_single(tmp_path: Path):
    p = tmp_path / "c0.jpg"
    Image.new("RGB", (80, 112), (10, 20, 30)).save(p)
    out = tmp_path / "single.jpg"
    build_card_grid([p], cols=1, rows=1, out_path=out, gap=0)
    assert Image.open(out).size == (80, 112)
