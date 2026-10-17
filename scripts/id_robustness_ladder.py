#!/usr/bin/env python3
"""
Staged robustness ladder for card ID on real binder YOLO crops.

Stages (cumulative):
  S0  Milo baseline (single crop)
  S1  Hybrid: OCR→Scryfall if confident, else Milo
  S2  Confidence gate (low scores → uncertain, not counted as auto-ID)
  S3  Orientation voting 0/90/180/270 (standard)
  S4  Dewarp + multi-skew views → majority vote + embedding mean fallback
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "scan" / "real" / "id_ladder"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "MagicOptimizer/1.0 (philipp; id-ladder)",
    "Accept": "application/json",
}

GT = {
    "binder_partial_4cards.png": [
        "Noxious Dragon",
        "Putrid Goblin",
        "Gleaming Geardrake",
        "Into the Roil",
    ],
    "binder_rotated_glare.png": [
        "Chittering Host",
        "Siege Zombie",
        "Village Rites",
        "Morkrut Banshee",
        "Elder Brain",
        "Gisa's Bidding",
        "Deadly Allure",
    ],
    "binder_red_glare.png": [
        "Fiery Temper",
        "Burning Prophet",
        "Kindle",
        "Incendiary Flow",
        "Twin Bolt",
        "Plasma Bolt",
        "Roughshod Duo",
    ],
}

ALIASES = {
    "putrid goblin": {"verwesender goblin", "putrid goblin"},
    "gleaming geardrake": {
        "glänzender mechasceada",
        "glänzender mechascada",
        "gleaming geardrake",
    },
    "into the roil": {"in die turbulenz hinein", "into the roil"},
    "elder brain": {"ältestengehirn", "altestengehirn", "ältestenhirn", "elder brain"},
    "burning prophet": {"feurige prophetin", "burning prophet"},
    "kindle": {"auflodern", "kindle"},
    "twin bolt": {"zwillingsblitz", "twin bolt"},
    "incendiary flow": {"flammenstrom", "incendiary flow"},
    "chittering host": {"chittering host"},
}

CONF_AUTO = 0.55
OCR_MIN_LEN = 5


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def name_match(pred: str, gt_list: list[str]) -> str | None:
    p = norm(pred)
    if not p or p.startswith("?") or p in {"unbekannt", "unknown", "e"} or len(p) < 4:
        return None
    p = p.lstrip("? ").strip()
    p_compact = re.sub(r"[^a-z0-9äöüß]", "", p)
    for g in gt_list:
        gn = norm(g)
        gn_compact = re.sub(r"[^a-z0-9äöüß]", "", gn)
        if p == gn or gn in p or (len(p) >= 6 and p in gn):
            return g
        if gn_compact and len(p_compact) >= 5 and (
            gn_compact in p_compact or p_compact in gn_compact
        ):
            return g
        for a in ALIASES.get(gn, set()):
            ac = re.sub(r"[^a-z0-9äöüß]", "", a)
            if p == a or a in p or (ac and len(ac) >= 5 and ac in p_compact):
                return g
    return None


def scryfall_named(name: str) -> dict | None:
    try:
        r = requests.get(
            "https://api.scryfall.com/cards/named",
            params={"fuzzy": name},
            headers=HEADERS,
            timeout=10,
        )
        time.sleep(0.07)
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


def scryfall_by_id(card_id: str) -> dict | None:
    try:
        r = requests.get(
            f"https://api.scryfall.com/cards/{card_id}",
            headers=HEADERS,
            timeout=10,
        )
        time.sleep(0.07)
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


def ocr_title(crop_bgr: np.ndarray) -> str | None:
    from rapidocr_onnxruntime import RapidOCR

    h, w = crop_bgr.shape[:2]
    title = crop_bgr[0 : max(int(h * 0.22), 12), :]
    if title.shape[1] < 220:
        title = cv2.resize(
            title,
            (title.shape[1] * 2, title.shape[0] * 2),
            interpolation=cv2.INTER_CUBIC,
        )
    tmp = OUT / "_ocr_tmp.jpg"
    cv2.imwrite(str(tmp), title)
    result, _ = RapidOCR()(str(tmp))
    tmp.unlink(missing_ok=True)
    if not result:
        return None
    text = " ".join(str(line[1]) for line in result if len(line) > 1).strip()
    return text or None


def rotate_image(img: np.ndarray, angle: int) -> np.ndarray:
    if angle % 360 == 0:
        return img
    if angle % 360 == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if angle % 360 == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle % 360 == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    # arbitrary
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), borderValue=(24, 28, 32))


def skew_image(img: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Small perspective-ish skew via affine."""
    h, w = img.shape[:2]
    src = np.float32([[0, 0], [w - 1, 0], [0, h - 1]])
    dst = np.float32(
        [
            [dx * w, dy * h],
            [w - 1 - dx * w, -dy * h],
            [-dx * w, h - 1 - dy * h],
        ]
    )
    m = cv2.getAffineTransform(src, dst)
    return cv2.warpAffine(img, m, (w, h), borderValue=(24, 28, 32))


@dataclass
class Pred:
    name: str
    score: float
    source: str
    uncertain: bool = False


class MiloEngine:
    def __init__(self):
        from collector_vision.catalog import Catalog
        from collector_vision.games import Game
        from collector_vision.detectors.neural import NeuralCornerDetector

        self.catalog = Catalog.for_game(Game.MTG)
        self.corners = NeuralCornerDetector(provider="cpu")
        self._name: dict[str, str] = {}

    def dewarp(self, crop: np.ndarray) -> np.ndarray:
        try:
            det = self.corners.detect(crop)
            if det is None:
                return crop
            warped = det.dewarp(crop)
            if warped is None or getattr(warped, "size", 0) == 0:
                return crop
            return warped
        except Exception:
            return crop

    def embed(self, crop: np.ndarray) -> np.ndarray:
        return self.catalog.embedder.embed(crop)

    def search_name(self, emb: np.ndarray, top_k: int = 1) -> list[tuple[str, float]]:
        hits = self.catalog.search(emb, top_k=top_k)
        out = []
        for score, card_id in hits:
            if card_id not in self._name:
                meta = scryfall_by_id(card_id)
                self._name[card_id] = meta["name"] if meta else card_id
            out.append((self._name[card_id], float(score)))
        return out

    def identify_one(self, crop: np.ndarray) -> Pred:
        warped = self.dewarp(crop)
        emb = self.embed(warped)
        hits = self.search_name(emb, top_k=1)
        if not hits:
            return Pred("Unbekannt", 0.0, "milo")
        name, score = hits[0]
        return Pred(name, score, "milo")

    def identify_rotations(self, crop: np.ndarray) -> Pred:
        best = Pred("Unbekannt", -1.0, "milo_rot")
        for angle in (0, 90, 180, 270):
            view = rotate_image(crop, angle)
            warped = self.dewarp(view)
            emb = self.embed(warped)
            hits = self.search_name(emb, top_k=1)
            if hits and hits[0][1] > best.score:
                best = Pred(hits[0][0], hits[0][1], f"milo_rot{angle}")
        return best

    def identify_ensemble(self, crop: np.ndarray) -> Pred:
        """Rotation + mild skews; majority vote, tie-break by mean embedding search."""
        views: list[np.ndarray] = []
        for angle in (0, 90, 180, 270):
            views.append(rotate_image(crop, angle))
        # mild skews on upright + 180
        for base_angle in (0, 180):
            base = rotate_image(crop, base_angle)
            for dx, dy in ((0.03, 0.0), (-0.03, 0.02), (0.02, -0.03), (0.04, 0.03)):
                views.append(skew_image(base, dx, dy))

        votes: list[tuple[str, float]] = []
        embs: list[np.ndarray] = []
        for view in views:
            warped = self.dewarp(view)
            emb = self.embed(warped)
            embs.append(np.asarray(emb, dtype=np.float32).reshape(-1))
            hits = self.search_name(emb, top_k=1)
            if hits and hits[0][1] >= 0.40:
                votes.append(hits[0])

        if votes:
            # majority by name, weighted by score
            scores: dict[str, float] = {}
            counts: Counter[str] = Counter()
            for name, sc in votes:
                counts[name] += 1
                scores[name] = scores.get(name, 0.0) + sc
            # prefer highest count, then highest sum score
            winner = max(counts.keys(), key=lambda n: (counts[n], scores[n]))
            avg_score = scores[winner] / counts[winner]
            return Pred(winner, float(avg_score), f"ensemble_vote_{counts[winner]}")

        # fallback: mean embedding
        if not embs:
            return Pred("Unbekannt", 0.0, "ensemble_empty")
        mean = np.mean(np.stack(embs, axis=0), axis=0)
        mean = mean / (np.linalg.norm(mean) + 1e-9)
        hits = self.search_name(mean, top_k=1)
        if not hits:
            return Pred("Unbekannt", 0.0, "ensemble_mean")
        return Pred(hits[0][0], hits[0][1], "ensemble_mean")


def yolo_crops(image_path: Path) -> list[np.ndarray]:
    import magic_optimizer.vision.yolo as yolo_mod

    yolo_mod._model = None
    from magic_optimizer.vision.detect import detect_card_regions

    img = cv2.imread(str(image_path))
    h, w = img.shape[:2]
    crops = []
    for d in detect_card_regions(str(image_path)):
        x1 = int(d["bbox_x"] * w)
        y1 = int(d["bbox_y"] * h)
        x2 = int((d["bbox_x"] + d["bbox_w"]) * w)
        y2 = int((d["bbox_y"] + d["bbox_h"]) * h)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 20 or y2 - y1 < 20:
            continue
        crops.append(img[y1:y2, x1:x2].copy())
    return crops


def hybrid_ocr(crop: np.ndarray, milo_pred: Pred) -> Pred:
    raw = ocr_title(crop)
    if not raw or len(raw.strip()) < OCR_MIN_LEN:
        return milo_pred
    # skip garbage like single letters / mostly digits
    letters = sum(c.isalpha() for c in raw)
    if letters < 4:
        return milo_pred
    meta = scryfall_named(raw)
    if not meta:
        return milo_pred
    # prefer OCR if Scryfall resolved and Milo is weak, or always if OCR looks good
    ocr_pred = Pred(meta["name"], 0.85, "ocr")
    if milo_pred.score < 0.60:
        return ocr_pred
    # if both strong, keep higher-confidence Milo unless OCR name differs and Milo is mediocre
    if milo_pred.score < 0.70:
        return ocr_pred
    return milo_pred


def gate(pred: Pred, thresh: float = CONF_AUTO) -> Pred:
    if pred.score < thresh and pred.source != "ocr":
        return Pred(pred.name, pred.score, pred.source, uncertain=True)
    return pred


def eval_stage(
    name: str,
    preds: list[tuple[str, Pred]],
    gt_by_photo: dict[str, list[str]],
) -> dict:
    """preds: list of (photo, Pred)."""
    hits = 0
    n = len(preds)
    auto_n = 0
    auto_hits = 0
    uncertain = 0
    for photo, pred in preds:
        gt = gt_by_photo[photo]
        matched = name_match(pred.name, gt)
        if pred.uncertain:
            uncertain += 1
            continue
        auto_n += 1
        if matched:
            hits += 1
            auto_hits += 1
        # also count raw hit ignoring gate for "coverage hit"
    raw_hits = sum(
        1
        for photo, pred in preds
        if name_match(pred.name, gt_by_photo[photo])
    )
    return {
        "stage": name,
        "crops": n,
        "raw_hits": raw_hits,
        "raw_pct": round(100 * raw_hits / n, 1) if n else 0,
        "auto_accepted": auto_n,
        "auto_hits": auto_hits,
        "auto_precision_pct": round(100 * auto_hits / auto_n, 1) if auto_n else 0,
        "uncertain": uncertain,
        "coverage_pct": round(100 * auto_n / n, 1) if n else 0,
    }


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "src"))

    print("Loading Milo…")
    milo = MiloEngine()

    # collect crops once
    items: list[tuple[str, np.ndarray]] = []
    real = ROOT / "tests/fixtures/scan/real"
    for fname in GT:
        path = real / fname
        crops = yolo_crops(path)
        print(f"{fname}: {len(crops)} crops")
        for c in crops:
            items.append((fname, c))

    # S0 baseline
    s0: list[tuple[str, Pred]] = []
    for photo, crop in items:
        s0.append((photo, milo.identify_one(crop)))
    m0 = eval_stage("S0_milo", s0, GT)

    # S1 hybrid
    s1: list[tuple[str, Pred]] = []
    for (photo, crop), (_, base) in zip(items, s0):
        s1.append((photo, hybrid_ocr(crop, base)))
    m1 = eval_stage("S1_hybrid_ocr", s1, GT)

    # S2 confidence gate on hybrid
    s2 = [(photo, gate(pred)) for photo, pred in s1]
    m2 = eval_stage("S2_conf_gate", s2, GT)

    # S3 rotation voting (then hybrid OCR override if milo weak)
    s3: list[tuple[str, Pred]] = []
    for photo, crop in items:
        rot = milo.identify_rotations(crop)
        s3.append((photo, gate(hybrid_ocr(crop, rot))))
    m3 = eval_stage("S3_rotation+hybrid+gate", s3, GT)

    # S4 ensemble skew/dewarp
    s4: list[tuple[str, Pred]] = []
    for photo, crop in items:
        ens = milo.identify_ensemble(crop)
        s4.append((photo, gate(hybrid_ocr(crop, ens))))
    m4 = eval_stage("S4_ensemble+hybrid+gate", s4, GT)

    ladder = [m0, m1, m2, m3, m4]
    print("\n======== LADDER ========")
    print(
        f"{'stage':28} raw_hit%  auto_prec%  coverage%  uncertain  auto_hits/auto"
    )
    for m in ladder:
        print(
            f"{m['stage']:28} {m['raw_pct']:6.1f}   {m['auto_precision_pct']:7.1f}   "
            f"{m['coverage_pct']:7.1f}   {m['uncertain']:4d}       "
            f"{m['auto_hits']}/{m['auto_accepted']}"
        )

    # per-crop detail for S3 and S4
    detail = []
    for i, ((photo, _crop), (_p0_photo, p0), (_p3_photo, p3), (_p4_photo, p4)) in enumerate(
        zip(items, s0, s3, s4)
    ):
        detail.append(
            {
                "i": i,
                "photo": photo,
                "s0": asdict(p0),
                "s3": asdict(p3),
                "s4": asdict(p4),
                "gt_hit_s0": bool(name_match(p0.name, GT[photo])),
                "gt_hit_s3": bool(name_match(p3.name, GT[photo])),
                "gt_hit_s4": bool(name_match(p4.name, GT[photo])),
            }
        )

    payload = {"ladder": ladder, "detail": detail}
    (OUT / "ladder_results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {OUT / 'ladder_results.json'}")

    # overlays for S3 (standard) and S4 (ensemble)
    from magic_optimizer.vision.overlay import render_overlay
    import magic_optimizer.vision.yolo as yolo_mod
    from magic_optimizer.vision.detect import detect_card_regions

    yolo_mod._model = None
    for stage_name, stage_preds in (("s3", s3), ("s4", s4)):
        overlay_dir = OUT / f"overlays_{stage_name}"
        overlay_dir.mkdir(exist_ok=True)
        idx = 0
        for fname in GT:
            path = real / fname
            dets = detect_card_regions(str(path))
            named = []
            for d in dets:
                if idx >= len(stage_preds):
                    break
                _photo, pred = stage_preds[idx]
                idx += 1
                label = pred.name if not pred.uncertain else f"? {pred.name}"
                status = "pending" if pred.uncertain else "accepted"
                named.append(
                    {
                        **d,
                        "detected_name": label,
                        "confidence": pred.score,
                        "status": status,
                    }
                )
            out_path = overlay_dir / f"{path.stem}_{stage_name}.jpg"
            render_overlay(str(path), named, str(out_path))
            print("overlay", out_path)


if __name__ == "__main__":
    main()
