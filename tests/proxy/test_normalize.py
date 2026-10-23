"""Normalize: center cover-crop then exact 488×680 (no stretch)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from magic_optimizer.proxy.normalize import cover_crop_box, normalize_image


def test_normalize_exact_size_and_cover_crop_no_stretch(tmp_path: Path):
    # Clearly non-matching aspect: very wide landscape (2:1) vs card ~0.72
    src = tmp_path / "wide_original.png"
    dest = tmp_path / "normalized" / "out.jpg"

    w, h = 1000, 500
    img = Image.new("RGB", (w, h), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    # Side bands — must be cropped away for portrait cover-crop
    draw.rectangle([0, 0, 199, h - 1], fill=(255, 0, 0))  # left red
    draw.rectangle([w - 200, 0, w - 1, h - 1], fill=(0, 0, 255))  # right blue
    # Center marker — must survive
    draw.rectangle([480, 220, 520, 280], fill=(0, 255, 0))
    img.save(src)

    # Original must not be mutated in place
    before_bytes = src.read_bytes()
    result = normalize_image(src, dest, width=488, height=680)
    assert result == dest.resolve()
    assert src.read_bytes() == before_bytes

    with Image.open(dest) as out:
        assert out.size == (488, 680)

        # Sample near left/right edges of output — side bands should be gone
        # (cover crop kept center 500×500 of the 1000×500 source ≈ grey/green)
        left_px = out.getpixel((5, 340))
        right_px = out.getpixel((482, 340))
        center_px = out.getpixel((244, 340))

    assert left_px[0] < 80, f"left edge still looks red/stretched: {left_px}"
    assert right_px[2] < 80, f"right edge still looks blue/stretched: {right_px}"
    # Center should be green-ish from the marker (LANCZOS softens edges)
    assert center_px[1] > center_px[0] and center_px[1] > center_px[2]


def test_cover_crop_box_wide_source():
    # 1000×500, target aspect 488/680
    box = cover_crop_box(1000, 500, 488 / 680)
    left, top, right, bottom = box
    assert top == 0 and bottom == 500
    crop_w = right - left
    crop_h = bottom - top
    assert abs((crop_w / crop_h) - (488 / 680)) < 0.01
    assert left > 0 and right < 1000


def test_normalize_refuses_overwrite_source(tmp_path: Path):
    src = tmp_path / "card.png"
    Image.new("RGB", (600, 900), color=(10, 10, 10)).save(src)
    try:
        normalize_image(src, src)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "overwrite" in str(exc).lower()
