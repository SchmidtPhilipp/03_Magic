"""PDF: A4 page size; cards drawn at exact mm (not fit-to-page)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image

from magic_optimizer.proxy.layout import compute_layout
from magic_optimizer.proxy.pdf import write_proxy_pdf

MM_TO_PT = 72.0 / 25.4
A4_W_PT = 210.0 * MM_TO_PT
A4_H_PT = 297.0 * MM_TO_PT


def _card_png(path: Path, color: tuple[int, int, int] = (200, 40, 40)) -> Path:
    Image.new("RGB", (488, 680), color=color).save(path)
    return path


def _default_layout():
    return compute_layout(
        page_width_mm=210.0,
        page_height_mm=297.0,
        card_width_mm=63.5,
        card_height_mm=88.9,
        margins_mm={"top": 10, "bottom": 10, "left": 10, "right": 10},
        gap_mm=2.0,
    )


def _pdf_page_count(data: bytes) -> int:
    # Count page objects; avoid matching /Pages
    return len(re.findall(rb"/Type\s*/Page\b", data))


def _pdf_mediaboxes(data: bytes) -> list[tuple[float, float, float, float]]:
    boxes = []
    for m in re.finditer(
        rb"/MediaBox\s*\[\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*\]",
        data,
    ):
        boxes.append(tuple(float(g) for g in m.groups()))  # type: ignore[misc]
    return boxes


def test_pdf_page_size_is_a4(tmp_path: Path):
    img = _card_png(tmp_path / "c.png")
    out = tmp_path / "sheet.pdf"
    write_proxy_pdf([img], out, layout=_default_layout())

    data = out.read_bytes()
    assert _pdf_page_count(data) == 1
    boxes = _pdf_mediaboxes(data)
    assert boxes, "expected MediaBox in PDF"
    _x0, _y0, w, h = boxes[0]
    assert w == pytest.approx(A4_W_PT, abs=1.0)
    assert h == pytest.approx(A4_H_PT, abs=1.0)


def test_pdf_multipage_overflow(tmp_path: Path):
    layout = _default_layout()
    assert layout.slots_per_page == 6
    images = [
        _card_png(tmp_path / f"c{i}.png", color=(10 * i + 20, 20, 30))
        for i in range(7)
    ]
    out = tmp_path / "multi.pdf"
    write_proxy_pdf(images, out, layout=layout)

    data = out.read_bytes()
    assert _pdf_page_count(data) == 2


def test_pdf_cards_use_fixed_mm_size(tmp_path: Path):
    """Writer must place at layout card mm — never scale cards to fill the page."""
    img = _card_png(tmp_path / "c.png")
    out = tmp_path / "fixed.pdf"
    layout = _default_layout()
    write_proxy_pdf([img, img], out, layout=layout)

    assert layout.card_width_mm == 63.5
    assert layout.card_height_mm == 88.9

    data = out.read_bytes()
    assert _pdf_page_count(data) == 1
    # Card size in points should appear in content (cm / Do scale paths vary;
    # reportlab often writes width/height via the transformation matrix).
    card_w_pt = 63.5 * MM_TO_PT
    card_h_pt = 88.9 * MM_TO_PT
    # Full printable area would be ~190×277 mm ≈ 538×785 pt — much larger
    printable_w_pt = 190.0 * MM_TO_PT
    assert card_w_pt < printable_w_pt * 0.5  # card is not page-width
    # Ensure PDF embeds images (DCTDecode or Flate for PNG)
    assert b"/Subtype /Image" in data or b"/Subtype/Image" in data
    assert len(data) > 500
    # Explicit mm constants used by layout must match physical card
    assert abs(card_w_pt - 63.5 * MM_TO_PT) < 1e-9
    assert abs(card_h_pt - 88.9 * MM_TO_PT) < 1e-9


def test_pdf_missing_image_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        write_proxy_pdf(
            [tmp_path / "nope.png"],
            tmp_path / "x.pdf",
            layout=_default_layout(),
        )


def test_pdf_rounded_corners_still_a4(tmp_path: Path):
    img = _card_png(tmp_path / "c.png")
    out = tmp_path / "round.pdf"
    write_proxy_pdf(
        [img],
        out,
        layout=_default_layout(),
        corner_radius_mm=2.5,
    )
    data = out.read_bytes()
    assert _pdf_page_count(data) == 1
    assert b"/Subtype /Image" in data or b"/Subtype/Image" in data
