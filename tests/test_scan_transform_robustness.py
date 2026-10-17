"""Robustness of card detection under mirror / skew / perspective."""

from pathlib import Path

import pytest

from magic_optimizer.vision.detect import detect_card_regions
from magic_optimizer.vision.fixtures import apply_scan_transform

BINDER = Path("tests/fixtures/scan/binder_3x3.jpg")
SINGLE = Path("tests/fixtures/scan/single.jpg")

# Soft floors: OpenCV contour detector on synthetic Scryfall grids.
BINDER_CASES = [
    ("identity", 9),
    ("mirror_h", 9),
    ("mirror_v", 9),
    ("rotate_15", 8),
    ("rotate_m20", 7),
    ("skew", 8),
    ("perspective", 8),
    ("perspective_strong", 7),
]

SINGLE_CASES = [
    ("identity", 1),
    ("mirror_h", 1),
    ("rotate_25", 1),
    ("perspective", 1),
]


@pytest.mark.skipif(not BINDER.exists(), reason="binder fixture missing")
@pytest.mark.parametrize("kind,minimum", BINDER_CASES)
def test_binder_detection_under_transform(kind, minimum, tmp_path):
    out = apply_scan_transform(BINDER, kind, tmp_path / f"binder_{kind}.jpg")
    n = len(detect_card_regions(str(out)))
    assert n >= minimum, f"{kind}: got {n}, want >= {minimum}"


@pytest.mark.skipif(not SINGLE.exists(), reason="single fixture missing")
@pytest.mark.parametrize("kind,minimum", SINGLE_CASES)
def test_single_detection_under_transform(kind, minimum, tmp_path):
    out = apply_scan_transform(SINGLE, kind, tmp_path / f"single_{kind}.jpg")
    n = len(detect_card_regions(str(out)))
    assert n >= minimum, f"{kind}: got {n}, want >= {minimum}"
