"""Draw review overlays (status-colored boxes + card names)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

_STATUS_COLORS = {
    "pending": (230, 170, 40),
    "accepted": (40, 200, 80),
    "rejected": (220, 50, 50),
}


def status_color(status: str) -> tuple[int, int, int]:
    """RGB outline/fill color for a detection status."""
    return _STATUS_COLORS.get(status, _STATUS_COLORS["pending"])


def render_overlay(
    image_path: str,
    detections: list[dict[str, Any]],
    output_path: str,
) -> str:
    """
    Render status-colored bounding boxes and labels onto the scan image.

    Returns output_path.
    """
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size
    font = ImageFont.load_default()

    for det in detections:
        status = det.get("status", "pending")
        color = status_color(status)
        x1 = det["bbox_x"] * width
        y1 = det["bbox_y"] * height
        x2 = x1 + det["bbox_w"] * width
        y2 = y1 + det["bbox_h"] * height
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        label = (det.get("detected_name") or "?").strip()[:48]
        if status == "accepted":
            label = f"✓ {label}"
        text_y = max(0, y1 - 14)
        text_bbox = draw.textbbox((x1, text_y), label, font=font)
        draw.rectangle(text_bbox, fill=color)
        draw.text((x1 + 2, text_y), label, fill=(0, 0, 0), font=font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="JPEG", quality=92)
    return output_path
