"""A4 grid layout for proxy cards at fixed physical size (no scaling)."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any, Mapping, Sequence

from magic_optimizer.proxy.config import ProxyConfig

# ISO 216 A4
A4_PORTRAIT_MM = (210.0, 297.0)
A4_LANDSCAPE_MM = (297.0, 210.0)


@dataclass(frozen=True)
class CardSlot:
    """One card cell on the page.

    Coordinates are millimetres from the **top-left** of the page
    (``x_mm`` = left edge, ``y_mm`` = top edge of the card).
    """

    col: int
    row: int
    x_mm: float
    y_mm: float


@dataclass(frozen=True)
class PageLayout:
    """Grid that maximizes cards without shrinking them below card mm size."""

    page_width_mm: float
    page_height_mm: float
    card_width_mm: float
    card_height_mm: float
    margins_mm: Mapping[str, float]
    gap_mm: float
    cols: int
    rows: int
    slots: tuple[CardSlot, ...]

    @property
    def slots_per_page(self) -> int:
        return self.cols * self.rows


def page_size_mm(
    *,
    orientation: str = "portrait",
    width_mm: float | None = None,
    height_mm: float | None = None,
) -> tuple[float, float]:
    """Return ``(width_mm, height_mm)`` for the page."""
    if width_mm is not None and height_mm is not None:
        w, h = float(width_mm), float(height_mm)
    else:
        orient = (orientation or "portrait").strip().lower()
        if orient == "landscape":
            w, h = A4_LANDSCAPE_MM
        else:
            w, h = A4_PORTRAIT_MM
    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid page size: {w}x{h} mm")
    return w, h


def max_fit(usable_mm: float, card_mm: float, gap_mm: float) -> int:
    """How many cards fit along one axis without scaling cards down."""
    if card_mm <= 0:
        raise ValueError(f"Invalid card size: {card_mm}")
    if usable_mm < card_mm:
        return 0
    gap = max(0.0, float(gap_mm))
    # n * card + (n - 1) * gap <= usable  →  n <= (usable + gap) / (card + gap)
    return int(floor((usable_mm + gap) / (card_mm + gap)))


def compute_layout(
    *,
    page_width_mm: float,
    page_height_mm: float,
    card_width_mm: float,
    card_height_mm: float,
    margins_mm: Mapping[str, float],
    gap_mm: float = 0.0,
    center_grid: bool = True,
) -> PageLayout:
    """Compute max cols/rows and top-left slot positions in mm.

    When ``center_grid`` is true, leftover space inside the printable area
    (after margins) is split evenly so the card grid is centered on both axes.
    """
    left = float(margins_mm.get("left", 0))
    right = float(margins_mm.get("right", 0))
    top = float(margins_mm.get("top", 0))
    bottom = float(margins_mm.get("bottom", 0))

    usable_w = page_width_mm - left - right
    usable_h = page_height_mm - top - bottom
    if usable_w <= 0 or usable_h <= 0:
        raise ValueError(
            f"Margins leave no printable area "
            f"({usable_w:.1f}×{usable_h:.1f} mm)"
        )

    cols = max_fit(usable_w, card_width_mm, gap_mm)
    rows = max_fit(usable_h, card_height_mm, gap_mm)
    if cols < 1 or rows < 1:
        raise ValueError(
            f"Card {card_width_mm}×{card_height_mm} mm does not fit "
            f"in printable area {usable_w:.1f}×{usable_h:.1f} mm "
            f"(margins={dict(margins_mm)}, gap={gap_mm})"
        )

    gap = max(0.0, float(gap_mm))
    grid_w = cols * card_width_mm + (cols - 1) * gap
    grid_h = rows * card_height_mm + (rows - 1) * gap
    if center_grid:
        origin_x = left + (usable_w - grid_w) / 2.0
        origin_y = top + (usable_h - grid_h) / 2.0
    else:
        origin_x = left
        origin_y = top

    slots: list[CardSlot] = []
    for row in range(rows):
        for col in range(cols):
            x = origin_x + col * (card_width_mm + gap)
            y = origin_y + row * (card_height_mm + gap)
            # Guard: card must stay inside printable area
            if x + card_width_mm > page_width_mm - right + 1e-6:
                raise ValueError(
                    f"Slot ({col},{row}) overflows right: "
                    f"x+w={x + card_width_mm:.3f} > {page_width_mm - right:.3f}"
                )
            if y + card_height_mm > page_height_mm - bottom + 1e-6:
                raise ValueError(
                    f"Slot ({col},{row}) overflows bottom: "
                    f"y+h={y + card_height_mm:.3f} > {page_height_mm - bottom:.3f}"
                )
            slots.append(CardSlot(col=col, row=row, x_mm=x, y_mm=y))

    return PageLayout(
        page_width_mm=float(page_width_mm),
        page_height_mm=float(page_height_mm),
        card_width_mm=float(card_width_mm),
        card_height_mm=float(card_height_mm),
        margins_mm={
            "top": top,
            "bottom": bottom,
            "left": left,
            "right": right,
        },
        gap_mm=gap,
        cols=cols,
        rows=rows,
        slots=tuple(slots),
    )


def layout_from_config(
    config: ProxyConfig,
    *,
    orientation: str | None = None,
) -> PageLayout:
    """Build a ``PageLayout`` from ``ProxyConfig`` (optional orientation override)."""
    page: Mapping[str, Any] = config.page or {}
    orient = orientation or str(page.get("orientation") or "portrait")

    if orientation is not None:
        # Explicit override → ISO A4 for that orientation (ignore config mm)
        page_w, page_h = page_size_mm(orientation=orient)
    else:
        width = page.get("width_mm")
        height = page.get("height_mm")
        page_w, page_h = page_size_mm(
            orientation=orient,
            width_mm=float(width) if width is not None else None,
            height_mm=float(height) if height is not None else None,
        )

    return compute_layout(
        page_width_mm=page_w,
        page_height_mm=page_h,
        card_width_mm=config.card_width_mm,
        card_height_mm=config.card_height_mm,
        margins_mm=config.margins_mm,
        gap_mm=config.gap_mm,
        center_grid=config.center_grid,
    )


def paginate_indices(total_cards: int, slots_per_page: int) -> Sequence[tuple[int, int]]:
    """Return ``(page_index, slot_index)`` for each card copy (0-based)."""
    if slots_per_page < 1:
        raise ValueError("slots_per_page must be >= 1")
    if total_cards < 0:
        raise ValueError("total_cards must be >= 0")
    out: list[tuple[int, int]] = []
    for i in range(total_cards):
        out.append((i // slots_per_page, i % slots_per_page))
    return out
