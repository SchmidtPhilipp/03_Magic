"""Tests for scan overlay rendering."""

import tempfile
from pathlib import Path

from PIL import Image

from magic_optimizer.vision.overlay import render_overlay, status_color


def test_status_colors():
    assert status_color("pending") == (230, 170, 40)
    assert status_color("accepted") == (40, 200, 80)
    assert status_color("rejected") == (220, 50, 50)


def test_render_overlay_writes_green_boxes():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src.jpg"
        out = Path(tmp) / "out.jpg"
        Image.new("RGB", (400, 300), color=(30, 30, 30)).save(src)
        detections = [
            {
                "bbox_x": 0.1,
                "bbox_y": 0.2,
                "bbox_w": 0.25,
                "bbox_h": 0.35,
                "detected_name": "Lightning Bolt",
                "status": "pending",
            }
        ]
        render_overlay(str(src), detections, str(out))
        assert out.exists()
        assert out.stat().st_size > 1000
