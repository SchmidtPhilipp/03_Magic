"""OCR helpers for card title regions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

_ocr_engine = None


def _get_ocr():
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    _ocr_engine = RapidOCR()
    return _ocr_engine


def ocr_title_from_bbox(image_path: str, det: dict[str, Any]) -> str | None:
    """Read title text from top ~30% of a card crop."""
    if cv2 is None:
        return None
    ocr = _get_ocr()
    if ocr is None:
        return None

    img = cv2.imread(image_path)
    if img is None:
        return None
    h, w = img.shape[:2]
    x1 = int(det["bbox_x"] * w)
    y1 = int(det["bbox_y"] * h)
    x2 = int((det["bbox_x"] + det["bbox_w"]) * w)
    y2 = int((det["bbox_y"] + det["bbox_h"]) * h)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None

    crop = img[y1:y2, x1:x2]
    title_h = max(int(crop.shape[0] * 0.32), 12)
    title = crop[0:title_h, :]
    if title.size == 0:
        return None

    scale = 2 if title.shape[1] < 200 else 1
    if scale > 1:
        title = cv2.resize(
            title,
            (title.shape[1] * scale, title.shape[0] * scale),
            interpolation=cv2.INTER_CUBIC,
        )

    tmp = Path(image_path).parent / "_ocr_tmp.jpg"
    cv2.imwrite(str(tmp), title)
    try:
        result, _ = ocr(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    if not result:
        return None
    text = " ".join(str(line[1]) for line in result if len(line) > 1).strip()
    return text or None


def enrich_detections_with_ocr(
    image_path: str, detections: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Fill detected_name from OCR when still unknown."""
    from magic_optimizer.vision.scryfall import lookup_card_name

    for det in detections:
        if det.get("detected_name") not in (None, "", "Unbekannt"):
            continue
        title = ocr_title_from_bbox(image_path, det)
        if not title:
            continue
        meta = lookup_card_name(title)
        if meta:
            det["detected_name"] = meta["card_name"]
            det["set_code"] = meta.get("set_code")
            det["scryfall_id"] = meta.get("scryfall_id")
            det["confidence"] = max(float(det.get("confidence") or 0), 0.55)
        else:
            det["detected_name"] = title
            det["confidence"] = max(float(det.get("confidence") or 0), 0.45)
    return detections
