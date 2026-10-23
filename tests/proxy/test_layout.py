"""Layout: grid math from A4 + margins + card mm + gap; no card scaling."""

from __future__ import annotations

import pytest

from magic_optimizer.proxy.config import ProxyConfig
from magic_optimizer.proxy.layout import (
    compute_layout,
    layout_from_config,
    max_fit,
    paginate_indices,
)


def test_max_fit_basic():
    # usable 190, card 63.5, gap 2 → (190+2)/(63.5+2) = 192/65.5 ≈ 2.93 → 2
    assert max_fit(190.0, 63.5, 2.0) == 2
    # With gap 0: 190/63.5 ≈ 2.99 → 2
    assert max_fit(190.0, 63.5, 0.0) == 2
    # Enough for 3: 3*63.5 + 2*2 = 194.5
    assert max_fit(194.5, 63.5, 2.0) == 3


def test_portrait_a4_wide_margins_is_2x3():
    # Wider margins (10 mm) → only 2×3 = 6 cards; top-left when not centered
    layout = compute_layout(
        page_width_mm=210.0,
        page_height_mm=297.0,
        card_width_mm=63.5,
        card_height_mm=88.9,
        margins_mm={"top": 10, "bottom": 10, "left": 10, "right": 10},
        gap_mm=2.0,
        center_grid=False,
    )
    assert layout.cols == 2
    assert layout.rows == 3
    assert layout.slots_per_page == 6
    assert len(layout.slots) == 6

    s0 = layout.slots[0]
    assert s0.col == 0 and s0.row == 0
    assert s0.x_mm == pytest.approx(10.0)
    assert s0.y_mm == pytest.approx(10.0)

    s1 = layout.slots[1]
    assert s1.col == 1 and s1.row == 0
    assert s1.x_mm == pytest.approx(10.0 + 63.5 + 2.0)

    right = 210.0 - 10.0
    bottom = 297.0 - 10.0
    for slot in layout.slots:
        assert slot.x_mm + 63.5 <= right + 1e-6
        assert slot.y_mm + 88.9 <= bottom + 1e-6


def test_portrait_a4_nine_up_margins_is_3x3():
    # Production config: L/R 5, T/B 8, gap 0 → 3×3 = 9 cards/page, centered
    layout = compute_layout(
        page_width_mm=210.0,
        page_height_mm=297.0,
        card_width_mm=63.5,
        card_height_mm=88.9,
        margins_mm={"top": 8, "bottom": 8, "left": 5, "right": 5},
        gap_mm=0.0,
        center_grid=True,
    )
    assert layout.cols == 3
    assert layout.rows == 3
    assert layout.slots_per_page == 9
    assert len(layout.slots) == 9

    # usable 200×281; grid 190.5×266.7 → origin (9.75, 15.15)
    s0 = layout.slots[0]
    assert s0.x_mm == pytest.approx(9.75)
    assert s0.y_mm == pytest.approx(15.15)

    right = 210.0 - 5.0
    bottom = 297.0 - 8.0
    for slot in layout.slots:
        assert slot.x_mm + 63.5 <= right + 1e-6
        assert slot.y_mm + 88.9 <= bottom + 1e-6

    # Horizontally & vertically centered leftovers match
    leftover_x = (210.0 - 5.0 - 5.0) - 3 * 63.5
    leftover_y = (297.0 - 8.0 - 8.0) - 3 * 88.9
    assert s0.x_mm == pytest.approx(5.0 + leftover_x / 2)
    assert s0.y_mm == pytest.approx(8.0 + leftover_y / 2)


def test_landscape_fits_more_columns():
    layout = compute_layout(
        page_width_mm=297.0,
        page_height_mm=210.0,
        card_width_mm=63.5,
        card_height_mm=88.9,
        margins_mm={"top": 10, "bottom": 10, "left": 10, "right": 10},
        gap_mm=2.0,
    )
    assert layout.cols == 4
    assert layout.rows == 2
    assert layout.slots_per_page == 8


def test_does_not_scale_cards_to_force_extra_column():
    # Printable width exactly fits 2 cards + gap; must not invent a 3rd by shrinking
    layout = compute_layout(
        page_width_mm=210.0,
        page_height_mm=297.0,
        card_width_mm=63.5,
        card_height_mm=88.9,
        margins_mm={"top": 10, "bottom": 10, "left": 10, "right": 10},
        gap_mm=2.0,
    )
    assert layout.card_width_mm == 63.5
    assert layout.card_height_mm == 88.9
    assert layout.cols == 2


def test_paginate_overflow():
    pages = paginate_indices(7, 6)
    assert pages == [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
        (1, 0),
    ]


def test_layout_from_config_uses_page_mm(tmp_path):
    cfg = ProxyConfig(
        reference_width=488,
        reference_height=680,
        card_width_mm=63.5,
        card_height_mm=88.9,
        page={
            "size": "A4",
            "orientation": "portrait",
            "width_mm": 210.0,
            "height_mm": 297.0,
        },
        margins_mm={"top": 10, "bottom": 10, "left": 10, "right": 10},
        gap_mm=2.0,
        center_grid=False,
        corner_radius_mm=2.5,
        paths={},
        root=tmp_path,
        raw={},
    )
    layout = layout_from_config(cfg)
    assert layout.cols == 2 and layout.rows == 3

    landscape = layout_from_config(cfg, orientation="landscape")
    assert landscape.page_width_mm == 297.0
    assert landscape.page_height_mm == 210.0
    assert landscape.cols == 4
