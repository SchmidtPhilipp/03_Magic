"""Write multi-page A4 proxy PDFs with cards at exact physical millimetre size."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from magic_optimizer.proxy.layout import PageLayout, paginate_indices

# Physical MTG-style default (~2.5 mm corner radius)
DEFAULT_CORNER_RADIUS_MM = 2.5


def _slot_index_for_draw(
    slot_i: int,
    *,
    cols: int,
    rows: int,
    mirror_horizontal: bool,
) -> int:
    """Map logical fill order → physical slot index (optional column mirror).

    For duplex long-edge flip, print backs with ``mirror_horizontal=True`` so
    backs align with fronts after flipping the sheet.
    """
    if not mirror_horizontal:
        return slot_i
    row = slot_i // cols
    col = slot_i % cols
    mirrored_col = cols - 1 - col
    return row * cols + mirrored_col


def write_proxy_pdf(
    image_paths: Sequence[Path | str],
    dest: Path | str,
    *,
    layout: PageLayout,
    corner_radius_mm: float = DEFAULT_CORNER_RADIUS_MM,
    mirror_horizontal: bool = False,
) -> Path:
    """Place each image at fixed card mm size; overflow starts a new page.

    Cards are **never** scaled to fit the page — each draw uses
    ``layout.card_width_mm`` × ``layout.card_height_mm``.
    Empty trailing slots on the last page are left blank.

    When ``corner_radius_mm`` > 0, each card is clipped to a rounded rectangle
    (MTG-like corners) before drawing.

    ``mirror_horizontal`` remaps columns (for duplex card backs).
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    paths = [Path(p) for p in image_paths]
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(f"Card image not found: {p}")

    page_w = layout.page_width_mm * mm
    page_h = layout.page_height_mm * mm
    card_w = layout.card_width_mm * mm
    card_h = layout.card_height_mm * mm
    radius = max(0.0, float(corner_radius_mm)) * mm
    # Cap radius so it cannot exceed half the shorter side
    max_r = min(card_w, card_h) / 2.0
    if radius > max_r:
        radius = max_r

    slots = layout.slots
    spp = layout.slots_per_page
    if spp < 1:
        raise ValueError("layout has no slots")

    c = canvas.Canvas(str(dest), pagesize=(page_w, page_h))

    if not paths:
        c.showPage()
        c.save()
        return dest.resolve()

    placements = paginate_indices(len(paths), spp)
    current_page = 0

    for card_i, (page_i, slot_i) in enumerate(placements):
        while current_page < page_i:
            c.showPage()
            current_page += 1

        draw_slot_i = _slot_index_for_draw(
            slot_i,
            cols=layout.cols,
            rows=layout.rows,
            mirror_horizontal=mirror_horizontal,
        )
        slot = slots[draw_slot_i]
        # layout y is from top of page; reportlab y is from bottom
        x = slot.x_mm * mm
        y = (layout.page_height_mm - slot.y_mm - layout.card_height_mm) * mm

        if x < -1e-6 or y < -1e-6:
            raise ValueError(f"Card {card_i} placed outside page (negative origin)")
        if x + card_w > page_w + 1e-6 or y + card_h > page_h + 1e-6:
            raise ValueError(
                f"Card {card_i} overflows page bounds "
                f"(x={slot.x_mm:.2f} y={slot.y_mm:.2f} mm)"
            )

        c.saveState()
        if radius > 0:
            path = c.beginPath()
            path.roundRect(x, y, card_w, card_h, radius)
            c.clipPath(path, stroke=0)
        c.drawImage(
            str(paths[card_i]),
            x,
            y,
            width=card_w,
            height=card_h,
            preserveAspectRatio=False,
            mask="auto",
        )
        c.restoreState()

    c.showPage()
    c.save()
    return dest.resolve()
