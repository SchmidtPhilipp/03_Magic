"""YOLO-based MTG card detection (Ultralytics)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_MODEL = os.environ.get(
    "MTG_YOLO_MODEL", str(Path("models") / "mtg_card" / "best.pt")
)
DEFAULT_CONF = float(os.environ.get("MTG_YOLO_CONF", "0.35"))

_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    path = Path(DEFAULT_MODEL)
    if not path.is_file():
        return None
    try:
        from ultralytics import YOLO
    except ImportError:
        return None
    _model = YOLO(str(path))
    return _model


def detect_with_yolo(
    image_path: str,
    conf: float | None = None,
) -> list[dict[str, Any]]:
    """
    Run YOLO inference; return normalized detections or [] if model missing.
    """
    model = _get_model()
    if model is None:
        return []

    threshold = conf if conf is not None else DEFAULT_CONF
    results = model.predict(image_path, conf=threshold, verbose=False)
    if not results:
        return []

    result = results[0]
    if result.boxes is None or len(result.boxes) == 0:
        return []

    height, width = result.orig_shape[:2]
    detections: list[dict[str, Any]] = []
    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        score = float(box.conf[0]) if box.conf is not None else 0.5
        bw = max(x2 - x1, 1)
        bh = max(y2 - y1, 1)
        detections.append(
            {
                "bbox_x": max(0.0, x1 / width),
                "bbox_y": max(0.0, y1 / height),
                "bbox_w": min(1.0, bw / width),
                "bbox_h": min(1.0, bh / height),
                "detected_name": "Unbekannt",
                "confidence": round(score, 3),
                "status": "pending",
                "source": "yolo",
            }
        )
    detections.sort(key=lambda d: (d["bbox_y"], d["bbox_x"]))
    return detections


def model_available() -> bool:
    return Path(DEFAULT_MODEL).is_file()
