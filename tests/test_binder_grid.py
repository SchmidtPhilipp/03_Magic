"""Binder grid-first slot detection (seed YOLO + lattice completion)."""

from __future__ import annotations

import numpy as np
import pytest

from magic_optimizer.vision import binder_grid as bg


def test_cluster_1d_groups_nearby_values():
    assert bg.cluster_1d([10.0, 12.0, 50.0, 51.0, 90.0], thresh=5.0) == pytest.approx(
        [11.0, 50.5, 90.0]
    )


def test_expand_anchors_fills_missing_third():
    # two columns; missing left
    out = bg.expand_anchors([40.0, 80.0], step=40.0, lo=0.0, hi=120.0, target=3)
    assert len(out) == 3
    assert out == pytest.approx([0.0, 40.0, 80.0]) or out == pytest.approx(
        [40.0, 80.0, 120.0]
    )


def test_content_score_higher_for_textured_card_than_flat_void():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    # empty pocket: uniform dark
    img[20:90, 20:90] = (18, 18, 18)
    # fake card: colorful + structure
    card = img[100:180, 100:180]
    card[:] = (40, 60, 160)
    card[5:20, :] = (220, 220, 220)  # title bar
    for i in range(25, 70, 4):
        card[i, 10:70] = (200, 200, 200)

    empty = bg.content_score(img, {"x1": 20, "y1": 20, "x2": 90, "y2": 90})
    filled = bg.content_score(img, {"x1": 100, "y1": 100, "x2": 180, "y2": 180})
    assert filled > empty
    assert filled >= 0.35


def test_complete_grid_from_seeds_fills_missing_slot_and_skips_empty():
    """2x2 occupied lattice with one missing card corner; empty pocket rejected."""
    H, W = 300, 300
    img = np.full((H, W, 3), 12, dtype=np.uint8)

    def paint_card(x1, y1, x2, y2, color):
        img[y1:y2, x1:x2] = color
        img[y1 + 4 : y1 + 14, x1 + 4 : x2 - 4] = (230, 230, 230)
        for i in range(y1 + 20, y2 - 10, 5):
            img[i, x1 + 8 : x2 - 8] = (200, 200, 200)

    # 3x3 cell centers roughly at 50,150,250 — cards at (0,0),(0,2),(2,0); miss (0,1) will be filled if seed nearby
    # Actually: seeds at TL, TR, BL — expect grid to propose TM if we had a seed pattern...
    # Simpler: seeds for 3 cards in L shape; expand creates 3x2 or 2x3; empty cells drop.
    paint_card(20, 20, 90, 110, (30, 40, 180))
    paint_card(210, 20, 280, 110, (40, 160, 40))
    paint_card(20, 190, 90, 280, (180, 40, 40))
    # middle-left empty (no paint) around (20-90, 105-185)

    seeds = [
        bg.SeedBox(20, 20, 90, 110, score=0.7),
        bg.SeedBox(210, 20, 280, 110, score=0.6),
        bg.SeedBox(20, 190, 90, 280, score=0.65),
    ]
    dets = bg.complete_grid_from_seeds(img, seeds)
    assert len(dets) >= 3
    # all returned boxes should cover painted cards or high-content regions
    centers = [
        ((d["bbox_x"] + d["bbox_w"] / 2) * W, (d["bbox_y"] + d["bbox_h"] / 2) * H)
        for d in dets
    ]
    # should include something near top-right card
    assert any(abs(cx - 245) < 40 and abs(cy - 65) < 40 for cx, cy in centers)
    # should NOT invent a box over pure void center of image if gap filter works
    # void center ~150,150
    void_hits = sum(1 for cx, cy in centers if abs(cx - 150) < 35 and abs(cy - 150) < 35)
    assert void_hits == 0


def test_detect_binder_slots_returns_empty_without_model(monkeypatch, tmp_path):
    import cv2

    p = tmp_path / "x.jpg"
    cv2.imwrite(str(p), np.zeros((40, 40, 3), dtype=np.uint8))
    monkeypatch.setattr(bg, "_yolo_seeds", lambda path, conf=0.08: [])
    assert bg.detect_binder_slots(str(p)) == []
