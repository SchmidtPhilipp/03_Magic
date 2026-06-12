"""OpenCV-based card region detection (YOLO replacement in Phase 2)."""

from __future__ import annotations

from typing import Any

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None
    np = None


def detect_card_regions(image_path: str) -> list[dict[str, Any]]:
    """
    Find card-like rectangles in a table photo.

    Returns normalized bboxes (0–1) with placeholder names until OCR/YOLO lands.
    """
    if cv2 is None:
        return []

    img = cv2.imread(image_path)
    if img is None:
        return []

    height, width = img.shape[:2]
    if height < 10 or width < 10:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = 0.008 * width * height
    detections: list[dict[str, Any]] = []

    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = bw * bh
        if area < min_area:
            continue
        aspect = bw / max(bh, 1)
        # MTG cards ~63×88 mm → portrait aspect ~0.72; allow skew/lighting variance
        if aspect < 0.45 or aspect > 1.05:
            continue
        if bw < width * 0.04 or bh < height * 0.04:
            continue

        detections.append(
            {
                "bbox_x": x / width,
                "bbox_y": y / height,
                "bbox_w": bw / width,
                "bbox_h": bh / height,
                "detected_name": "Unbekannt",
                "confidence": 0.4,
                "status": "pending",
            }
        )

    detections = _suppress_overlaps(detections)
    detections.sort(key=lambda d: (d["bbox_y"], d["bbox_x"]))
    return detections


def _suppress_overlaps(
    detections: list[dict[str, Any]], iou_threshold: float = 0.45
) -> list[dict[str, Any]]:
    """Drop smaller boxes that heavily overlap a larger one."""
    if not detections:
        return []

    def area(d: dict[str, Any]) -> float:
        return d["bbox_w"] * d["bbox_h"]

    ordered = sorted(detections, key=area, reverse=True)
    kept: list[dict[str, Any]] = []
    for candidate in ordered:
        if all(_iou(candidate, k) < iou_threshold for k in kept):
            kept.append(candidate)
    return kept


def _iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax2 = a["bbox_x"] + a["bbox_w"]
    ay2 = a["bbox_y"] + a["bbox_h"]
    bx2 = b["bbox_x"] + b["bbox_w"]
    by2 = b["bbox_y"] + b["bbox_h"]
    ix1 = max(a["bbox_x"], b["bbox_x"])
    iy1 = max(a["bbox_y"], b["bbox_y"])
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = a["bbox_w"] * a["bbox_h"] + b["bbox_w"] * b["bbox_h"] - inter
    return inter / max(union, 1e-9)
