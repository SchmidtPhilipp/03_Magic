#!/usr/bin/env python3
"""Bakeoff: OCR+Scryfall vs CollectorVision(Milo) vs dhvazquez embeddings on real binder crops."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "scan" / "real" / "id_bakeoff"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "MagicOptimizer/1.0 (philipp; id-bakeoff)",
    "Accept": "application/json",
}

# Ground-truth English oracle names for cards present in each photo
# (German printings still resolve to these via Scryfall).
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
        "Magma Spray",  # Flammenstrom may be Magma Jet / Magma Spray — verify
        "Twin Bolt",
        "Plasma Bolt",
        "Roughshod Duo",
    ],
}

# Alternate German/EN names we accept as hits
ALIASES = {
    "putrid goblin": {"verwesender goblin", "putrid goblin"},
    "gleaming geardrake": {"glänzender mechasceada", "glänzender mechascada", "gleaming geardrake"},
    "into the roil": {"in die turbulenz hinein", "into the roil"},
    "elder brain": {"ältestengehirn", "ältestenhirn", "elder brain"},
    "burning prophet": {"feurige prophetin", "burning prophet"},
    "kindle": {"auflodern", "kindle"},
    "twin bolt": {"zwillingsblitz", "twin bolt"},
    "magma spray": {"flammenstrom", "magma spray", "magma jet"},
    "chittering host": {"chittering host", "hanweir battlements", "hanweir garrison"},
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def name_match(pred: str, gt_list: list[str]) -> str | None:
    p = norm(pred)
    if not p or p in {"unbekannt", "unknown", "?", "e"} or len(p) < 4:
        return None
    p_compact = re.sub(r"[^a-z0-9äöüß]", "", p)
    for g in gt_list:
        gn = norm(g)
        gn_compact = re.sub(r"[^a-z0-9äöüß]", "", gn)
        if p == gn or gn in p or (len(p) >= 6 and p in gn):
            return g
        if gn_compact and (gn_compact in p_compact or p_compact in gn_compact):
            return g
        al = ALIASES.get(gn, set())
        for a in al:
            ac = re.sub(r"[^a-z0-9äöüß]", "", a)
            if p == a or a in p or (ac and ac in p_compact):
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
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


def ocr_title(crop_bgr: np.ndarray) -> str | None:
    from rapidocr_onnxruntime import RapidOCR

    h, w = crop_bgr.shape[:2]
    title = crop_bgr[0 : max(int(h * 0.22), 12), :]
    scale = 2 if title.shape[1] < 220 else 1
    if scale > 1:
        title = cv2.resize(
            title,
            (title.shape[1] * scale, title.shape[0] * scale),
            interpolation=cv2.INTER_CUBIC,
        )
    tmp = OUT / "_ocr_tmp.jpg"
    cv2.imwrite(str(tmp), title)
    ocr = RapidOCR()
    result, _ = ocr(str(tmp))
    tmp.unlink(missing_ok=True)
    if not result:
        return None
    text = " ".join(str(line[1]) for line in result if len(line) > 1).strip()
    return text or None


class DhvazquezID:
    def __init__(self):
        onnx = ROOT / "models/mtg_id/20260521-044732/onnx/mtg_embed_fp16.onnx"
        gal = ROOT / "models/mtg_id/20260521-044732/gallery_val.npz"
        self.sess = ort.InferenceSession(
            str(onnx), providers=["CPUExecutionProvider"]
        )
        g = np.load(gal, allow_pickle=True)
        emb = g["embeddings"].astype(np.float32)
        # L2 normalize
        emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
        self.emb = emb
        self.labels = g["labels"]
        self._id_cache: dict[str, str] = {}

    def embed(self, crop_bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(rgb, (320, 448), interpolation=cv2.INTER_AREA)
        x = img.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = (x - mean) / std
        x = np.transpose(x, (2, 0, 1))[None, ...].astype(np.float16)
        out = self.sess.run(None, {self.sess.get_inputs()[0].name: x})[0]
        v = out[0].astype(np.float32)
        v /= np.linalg.norm(v) + 1e-9
        return v

    def identify(self, crop_bgr: np.ndarray) -> tuple[str, float]:
        v = self.embed(crop_bgr)
        sims = self.emb @ v
        idx = int(np.argmax(sims))
        score = float(sims[idx])
        label = str(self.labels[idx])
        # label: oracle_or_other__{scryfall_id}_{set}_{num}_{lang}_normal
        if "__" in label:
            card_id = label.split("__", 1)[1].split("_", 1)[0]
        else:
            card_id = label.split("_", 1)[0]
        if card_id not in self._id_cache:
            meta = scryfall_by_id(card_id)
            time.sleep(0.08)
            self._id_cache[card_id] = (
                meta.get("name", card_id) if meta else card_id
            )
        return self._id_cache[card_id], score


class MiloID:
    def __init__(self):
        from collector_vision.catalog import Catalog
        from collector_vision.games import Game
        from collector_vision.detectors.neural import NeuralCornerDetector

        self.catalog = Catalog.for_game(Game.MTG)
        self.corners = NeuralCornerDetector(provider="cpu")
        self._id_cache: dict[str, str] = {}

    def identify(self, crop_bgr: np.ndarray) -> tuple[str, float]:
        # Prefer dewarp via corner detector; fall back to raw crop embed
        try:
            det = self.corners.detect(crop_bgr)
            warped = det.dewarp(crop_bgr) if det is not None else crop_bgr
        except Exception:
            warped = crop_bgr
        if warped is None or getattr(warped, "size", 0) == 0:
            warped = crop_bgr
        emb = self.catalog.embedder.embed(warped)
        hits = self.catalog.search(emb, top_k=1)
        if not hits:
            return "?", 0.0
        score, card_id = hits[0]
        if card_id not in self._id_cache:
            meta = scryfall_by_id(card_id)
            time.sleep(0.08)
            self._id_cache[card_id] = (
                meta.get("name", card_id) if meta else card_id
            )
        return self._id_cache[card_id], float(score)


def yolo_crops(image_path: Path) -> list[tuple[np.ndarray, dict]]:
    import magic_optimizer.vision.yolo as yolo_mod

    yolo_mod._model = None
    from magic_optimizer.vision.detect import detect_card_regions

    img = cv2.imread(str(image_path))
    h, w = img.shape[:2]
    dets = detect_card_regions(str(image_path))
    crops = []
    for d in dets:
        x1 = int(d["bbox_x"] * w)
        y1 = int(d["bbox_y"] * h)
        x2 = int((d["bbox_x"] + d["bbox_w"]) * w)
        y2 = int((d["bbox_y"] + d["bbox_h"]) * h)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 20 or y2 - y1 < 20:
            continue
        crops.append((img[y1:y2, x1:x2].copy(), d))
    return crops


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "src"))

    print("Loading identifiers…")
    milo = MiloID()
    dhv = DhvazquezID()

    summary = {
        "ocr_scryfall": {"hits": 0, "n": 0},
        "collectorvision_milo": {"hits": 0, "n": 0},
        "dhvazquez_embed": {"hits": 0, "n": 0},
    }
    rows = []

    real = ROOT / "tests/fixtures/scan/real"
    for fname, gt in GT.items():
        path = real / fname
        if not path.exists():
            print("missing", path)
            continue
        print(f"\n=== {fname} (GT={len(gt)}) ===")
        crops = yolo_crops(path)
        print(f"YOLO crops: {len(crops)}")
        gt_remaining = list(gt)
        photo_dir = OUT / path.stem
        photo_dir.mkdir(exist_ok=True)

        for i, (crop, det) in enumerate(crops):
            cv2.imwrite(str(photo_dir / f"crop_{i:02d}.jpg"), crop)

            # OCR
            t0 = time.time()
            raw = ocr_title(crop)
            meta = scryfall_named(raw) if raw else None
            ocr_name = meta["name"] if meta else (raw or "?")
            ocr_ms = (time.time() - t0) * 1000
            time.sleep(0.08)

            # Milo
            t0 = time.time()
            try:
                milo_name, milo_score = milo.identify(crop)
            except Exception as exc:
                milo_name, milo_score = f"[err {exc}]", 0.0
            milo_ms = (time.time() - t0) * 1000

            # dhvazquez
            t0 = time.time()
            try:
                dhv_name, dhv_score = dhv.identify(crop)
            except Exception as exc:
                dhv_name, dhv_score = f"[err {exc}]", 0.0
            dhv_ms = (time.time() - t0) * 1000

            ocr_hit = name_match(ocr_name, gt)
            milo_hit = name_match(milo_name, gt)
            dhv_hit = name_match(dhv_name, gt)

            summary["ocr_scryfall"]["n"] += 1
            summary["collectorvision_milo"]["n"] += 1
            summary["dhvazquez_embed"]["n"] += 1
            if ocr_hit:
                summary["ocr_scryfall"]["hits"] += 1
            if milo_hit:
                summary["collectorvision_milo"]["hits"] += 1
            if dhv_hit:
                summary["dhvazquez_embed"]["hits"] += 1

            row = {
                "photo": fname,
                "crop": i,
                "ocr_raw": raw,
                "ocr_name": ocr_name,
                "ocr_hit": ocr_hit,
                "ocr_ms": round(ocr_ms, 1),
                "milo_name": milo_name,
                "milo_score": round(milo_score, 3),
                "milo_hit": milo_hit,
                "milo_ms": round(milo_ms, 1),
                "dhv_name": dhv_name,
                "dhv_score": round(dhv_score, 3),
                "dhv_hit": dhv_hit,
                "dhv_ms": round(dhv_ms, 1),
            }
            rows.append(row)
            print(
                f"  crop{i}: OCR={ocr_name!r}{'✓' if ocr_hit else '✗'} | "
                f"Milo={milo_name!r}{'✓' if milo_hit else '✗'}({milo_score:.2f}) | "
                f"Dhv={dhv_name!r}{'✓' if dhv_hit else '✗'}({dhv_score:.2f})"
            )

    print("\n======== SUMMARY (hits / YOLO-crops) ========")
    for k, v in summary.items():
        rate = (100.0 * v["hits"] / v["n"]) if v["n"] else 0
        print(f"{k:24s}  {v['hits']:2d}/{v['n']:2d}  ({rate:.0f}%)")

    (OUT / "results.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
