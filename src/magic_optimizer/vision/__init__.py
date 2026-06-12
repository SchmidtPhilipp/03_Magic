"""Computer vision helpers for table-scan card detection."""

from __future__ import annotations

from magic_optimizer.vision.detect import detect_card_regions
from magic_optimizer.vision.overlay import render_overlay
from magic_optimizer.vision.scryfall import lookup_card_name

__all__ = ["detect_card_regions", "render_overlay", "lookup_card_name"]
