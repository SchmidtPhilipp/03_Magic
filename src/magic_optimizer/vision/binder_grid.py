"""Binder grid-first detection: YOLO seeds → lattice completion → occupancy filter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

YOLO_SEED_CONF = 0.05
YOLO_STRONG = 0.25
CONTENT_ABS_FLOOR = 0.50
NMS_IOU = 0.45
MARGIN_MIN_CX = 0.08
MARGIN_MAX_CX = 0.88


@dataclass
class SeedBox:
    x1: float
    y1: float
    x2: float
    y2: float
    score: float = 0.5

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def w(self) -> float:
        return self.x2 - self.x1

    @property
    def h(self) -> float:
        return self.y2 - self.y1

    def as_dict(self) -> dict[str, float]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "cx": self.cx,
            "cy": self.cy,
            "w": self.w,
            "h": self.h,
            "score": self.score,
        }


def cluster_1d(vals: list[float], thresh: float) -> list[float]:
    if not vals:
        return []
    ordered = sorted(float(v) for v in vals)
    clusters: list[list[float]] = [[ordered[0]]]
    for v in ordered[1:]:
        if abs(v - float(np.mean(clusters[-1]))) > thresh:
            clusters.append([v])
        else:
            clusters[-1].append(v)
    return [float(np.mean(c)) for c in clusters]


def expand_anchors(
    anchors: list[float],
    step: float,
    lo: float,
    hi: float,
    target: int = 3,
) -> list[float]:
    anchors = sorted(float(a) for a in anchors)
    if not anchors:
        return []
    if len(anchors) >= target:
        if len(anchors) == target:
            return anchors
        return [anchors[0], anchors[len(anchors) // 2], anchors[-1]][:target]

    step = max(float(step), 1.0)
    while len(anchors) < target:
        cands: list[float] = []
        for a in anchors:
            for c in (a - step, a + step):
                if lo - 0.2 * step <= c <= hi + 0.2 * step and all(
                    abs(c - x) > step * 0.4 for x in anchors
                ):
                    cands.append(c)
        if not cands:
            break

        def pen(c: float) -> float:
            s = sorted(anchors + [c])
            return float(np.std(np.diff(s)))

        cands.sort(key=pen)
        anchors = sorted(anchors + [cands[0]])
    return anchors


def _iou(a: dict[str, float], b: dict[str, float]) -> float:
    ix1 = max(a["x1"], b["x1"])
    iy1 = max(a["y1"], b["y1"])
    ix2 = min(a["x2"], b["x2"])
    iy2 = min(a["y2"], b["y2"])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    ua = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"]) + (b["x2"] - b["x1"]) * (
        b["y2"] - b["y1"]
    ) - inter
    return float(inter / max(ua, 1e-9))


def _iou_norm(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax = {
        "x1": a["bbox_x"],
        "y1": a["bbox_y"],
        "x2": a["bbox_x"] + a["bbox_w"],
        "y2": a["bbox_y"] + a["bbox_h"],
    }
    bx = {
        "x1": b["bbox_x"],
        "y1": b["bbox_y"],
        "x2": b["bbox_x"] + b["bbox_w"],
        "y2": b["bbox_y"] + b["bbox_h"],
    }
    return _iou(ax, bx)


def content_score(img: np.ndarray, box: dict[str, float]) -> float:
    """How card-like is the crop (vs empty black pocket)."""
    if cv2 is None:
        return 0.0
    h, w = img.shape[:2]
    x1 = int(max(0, box["x1"]))
    y1 = int(max(0, box["y1"]))
    x2 = int(min(w, box["x2"]))
    y2 = int(min(h, box["y2"]))
    bw, bh = x2 - x1, y2 - y1
    if bw < 12 or bh < 12:
        return 0.0
    ix, iy = int(0.12 * bw), int(0.12 * bh)
    crop = img[y1 + iy : y2 - iy, x1 + ix : x2 - ix]
    if crop.size == 0 or min(crop.shape[:2]) < 8:
        return 0.0

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    std = float(gray.std())
    edge = float(cv2.Canny(gray, 50, 150).mean())
    sat = float(hsv[:, :, 1].mean())
    b, g, r = cv2.split(crop.astype(np.float32))
    chroma = float(np.mean(np.abs(r - g) + np.abs(g - b) + np.abs(b - r)) / 3)
    row_var = float(np.var(gray.mean(axis=1)))
    return float(
        0.2 * min(lap / 250, 1)
        + 0.15 * min(std / 35, 1)
        + 0.15 * min(edge / 22, 1)
        + 0.2 * min(sat / 50, 1)
        + 0.15 * min(chroma / 25, 1)
        + 0.15 * min(row_var / 400, 1)
    )


def occupancy_threshold(scores: list[float]) -> float:
    """
    Decide occupied vs empty.

    Prefer a gap that separates a *low* empty cluster from cards.
    Ignore gaps that only peel off a single high outlier (old bug).
    Fallback: absolute content floor.
    """
    if not scores:
        return CONTENT_ABS_FLOOR
    ss = np.sort(np.asarray(scores, dtype=np.float64))
    if len(ss) < 2:
        return CONTENT_ABS_FLOOR
    gaps = np.diff(ss)
    # consider gaps from lowest upward; pick best that separates empty-looking cluster
    best_thresh = None
    best_gap = 0.0
    for gi, gap in enumerate(gaps):
        if gap < 0.12:
            continue
        lo = ss[: gi + 1]
        hi = ss[gi + 1 :]
        lo_mean = float(np.mean(lo))
        hi_mean = float(np.mean(hi))
        # empty cluster should be clearly low; high side card-like
        if lo_mean < 0.55 and hi_mean >= 0.55 and (hi_mean - lo_mean) >= 0.15:
            if gap > best_gap:
                best_gap = float(gap)
                best_thresh = float((ss[gi] + ss[gi + 1]) / 2)
    if best_thresh is not None:
        return max(CONTENT_ABS_FLOOR - 0.05, min(best_thresh, 0.65))
    return CONTENT_ABS_FLOOR


# Back-compat alias used by older ablation scripts
def _gap_threshold(scores: list[float]) -> float:
    return occupancy_threshold(scores)


def nms_detections(
    dets: list[dict[str, Any]], iou_thresh: float = NMS_IOU
) -> list[dict[str, Any]]:
    if not dets:
        return []
    ordered = sorted(dets, key=lambda d: float(d.get("confidence") or 0), reverse=True)
    kept: list[dict[str, Any]] = []
    for d in ordered:
        if all(_iou_norm(d, k) < iou_thresh for k in kept):
            kept.append(d)
    kept.sort(key=lambda d: (d["bbox_y"], d["bbox_x"]))
    return kept


def filter_page_margins(
    dets: list[dict[str, Any]],
    *,
    min_cx: float = MARGIN_MIN_CX,
    max_cx: float = MARGIN_MAX_CX,
) -> list[dict[str, Any]]:
    """Drop boxes centered on binder rings / far outside the page grid."""
    out = []
    for d in dets:
        cx = float(d["bbox_x"]) + float(d["bbox_w"]) / 2
        if cx < min_cx or cx > max_cx:
            continue
        out.append(d)
    return out


def _yolo_seeds(image_path: str, conf: float = YOLO_SEED_CONF) -> list[SeedBox]:
    try:
        from ultralytics import YOLO
        from magic_optimizer.vision.yolo import DEFAULT_MODEL, model_available
    except ImportError:
        return []
    if not model_available():
        return []
    from pathlib import Path

    model = YOLO(str(Path(DEFAULT_MODEL)))
    results = model.predict(image_path, conf=conf, verbose=False)
    if not results or results[0].boxes is None:
        return []
    result = results[0]
    h, w = result.orig_shape[:2]
    seeds: list[SeedBox] = []
    for box in result.boxes:
        x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
        score = float(box.conf[0]) if box.conf is not None else 0.5
        bw, bh = x2 - x1, y2 - y1
        if bw * bh > 0.22 * w * h or bw > 0.5 * w:
            continue
        if not (0.45 <= bw / max(bh, 1) <= 1.65):
            continue
        # binder-ring-ish far-right / far-left
        cx = (x1 + x2) / 2 / w
        if cx < 0.08 or cx > 0.88:
            continue
        seeds.append(SeedBox(x1, y1, x2, y2, score=score))
    return seeds


def _pick_three_anchors(
    anchors: list[float], seed_vals: list[float], seed_scores: list[float]
) -> list[float]:
    """
    When clustering yields >3 anchors (e.g. ring + 3 cols), keep the 3 with
    strongest seed mass — not first/mid/last (which drops the center column).
    """
    if len(anchors) <= 3:
        return anchors
    mass = []
    for a in anchors:
        m = 0.0
        for v, sc in zip(seed_vals, seed_scores):
            if abs(v - a) < abs(anchors[1] - anchors[0]) * 0.45 if len(anchors) > 1 else 1e9:
                m += sc
        mass.append((m, a))
    mass.sort(reverse=True)
    return sorted(a for _, a in mass[:3])


def complete_grid_from_seeds(
    img: np.ndarray,
    seeds: list[SeedBox],
) -> list[dict[str, Any]]:
    """
    Build up to a 3×3 lattice from seed boxes; keep strong YOLO or high content.
    Returns normalized detection dicts (bbox_*, confidence, source).
    """
    if cv2 is None or len(seeds) < 2:
        return []

    h, w = img.shape[:2]
    # Prefer mid-confidence seeds for size estimate (avoid giant FP boxes)
    sized = sorted(seeds, key=lambda s: s.score, reverse=True)
    sized = sized[: max(3, len(sized) // 2)] or seeds
    mw = float(np.median([s.w for s in sized]))
    mh = float(np.median([s.h for s in sized]))
    if mw < 8 or mh < 8:
        return []

    # Drop huge non-card seeds before clustering
    seeds = [
        s
        for s in seeds
        if s.w <= mw * 1.55 and s.h <= mh * 1.55 and s.w * s.h <= 0.18 * w * h
    ]
    if len(seeds) < 2:
        return []

    cols = cluster_1d([s.cx for s in seeds], mw * 0.55)
    rows = cluster_1d([s.cy for s in seeds], mh * 0.55)
    if len(cols) < 2 and len(rows) < 2:
        return []

    if len(cols) > 3:
        cols = _pick_three_anchors(cols, [s.cx for s in seeds], [s.score for s in seeds])
    if len(rows) > 3:
        rows = _pick_three_anchors(rows, [s.cy for s in seeds], [s.score for s in seeds])

    step_x = float(np.median(np.diff(cols))) if len(cols) >= 2 else mw * 1.15
    step_y = float(np.median(np.diff(rows))) if len(rows) >= 2 else mh * 1.15
    cols = expand_anchors(cols, step_x, 0.0, float(w))
    rows = expand_anchors(rows, step_y, 0.0, float(h))

    seed_dicts = [s.as_dict() for s in seeds]
    cells: list[dict[str, Any]] = []
    for cy in rows:
        for cx in cols:
            lattice = {
                "x1": cx - mw / 2,
                "y1": cy - mh / 2,
                "x2": cx + mw / 2,
                "y2": cy + mh / 2,
            }
            best = None
            best_iou = 0.0
            for sd in seed_dicts:
                i = _iou(lattice, sd)
                if i > best_iou:
                    best_iou = i
                    best = sd

            yolo = float(best["score"]) if best is not None and best_iou >= 0.2 else 0.0
            if yolo >= YOLO_STRONG and best is not None:
                box = best
                src = "yolo"
                score = content_score(img, box)
            else:
                box = lattice
                src = "grid"
                score = content_score(img, box)
                if best is not None and best_iou >= 0.2:
                    s2 = content_score(img, best)
                    if s2 > score:
                        score = s2
                        box = best
                        src = "yolo_weak"
            cells.append(
                {"box": box, "yolo": yolo, "score": score, "src": src, "cx": cx, "cy": cy}
            )

    thresh = occupancy_threshold([c["score"] for c in cells])
    pure_grid_floor = max(thresh, 0.64)
    out: list[dict[str, Any]] = []
    for c in cells:
        yolo, score = c["yolo"], c["score"]
        # Even strong YOLO needs some content — empty pockets can score ~0.35–0.45.
        if yolo >= 0.45 and score >= 0.48:
            keep, src = True, "yolo"
        elif yolo >= YOLO_STRONG and score >= 0.50:
            keep, src = True, "yolo"
        elif yolo >= 0.15 and score >= max(thresh, 0.58):
            keep, src = True, c["src"]
        elif 0.10 <= yolo < 0.15 and score >= 0.68:
            # very weak YOLO: only keep if content is clearly card-like
            keep, src = True, c["src"]
        elif yolo < 0.10 and score >= pure_grid_floor:
            keep, src = True, c["src"]
        else:
            keep, src = False, c["src"]
        if not keep:
            continue
        b = c["box"]
        out.append(
            {
                "bbox_x": float(b["x1"] / w),
                "bbox_y": float(b["y1"] / h),
                "bbox_w": float((b["x2"] - b["x1"]) / w),
                "bbox_h": float((b["y2"] - b["y1"]) / h),
                "detected_name": "Unbekannt",
                "confidence": round(float(max(yolo, score)), 3),
                "status": "pending",
                "source": f"binder_{src}",
            }
        )
    out = filter_page_margins(out)
    out = nms_detections(out)
    return out


def detect_binder_slots(image_path: str) -> list[dict[str, Any]]:
    """
    Grid-first binder detection. Returns [] if not binder-like / model missing.
    """
    if cv2 is None:
        return []
    img = cv2.imread(image_path)
    if img is None:
        return []
    seeds = _yolo_seeds(image_path)
    if len(seeds) < 2:
        return []
    return complete_grid_from_seeds(img, seeds)
