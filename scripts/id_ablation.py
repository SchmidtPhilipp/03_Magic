#!/usr/bin/env python3
"""
Scientific ablation of ID robustness ideas on fixed binder_grid crops.

Ideas under test (vs baseline S3):
  A1  inset crop 8% / 12% before ID
  A2  CLAHE contrast on crop
  A3  best-of preprocess (raw / inset8 / clahe) by Milo rotation score
  B1  collector# OCR tie-break when Milo top-2 are close
  B2  Milo top-3 + title-OCR rerank (Scryfall)

Only spatial 1:1 GT matching counts as a hit. Results → JSON; no pipeline change here.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "tests/fixtures/scan/real/id_ablation"
OUT.mkdir(parents=True, exist_ok=True)

# Approximate slot centers (norm) for 1:1 assignment
GT_SLOTS: dict[str, list[tuple[float, float, str]]] = {
    "binder_partial_4cards.png": [
        (0.25, 0.28, "Noxious Dragon"),
        (0.72, 0.28, "Putrid Goblin"),
        (0.72, 0.55, "Gleaming Geardrake"),
        (0.25, 0.82, "Into the Roil"),
    ],
    "binder_rotated_glare.png": [
        (0.22, 0.28, "Chittering Host"),
        (0.45, 0.28, "Eldrazi Horror"),
        (0.68, 0.28, "Siege Zombie"),
        (0.22, 0.52, "Village Rites"),
        (0.45, 0.52, "Morkrut Banshee"),
        (0.68, 0.52, "Elder Brain"),
        (0.45, 0.78, "Gisa's Bidding"),
        (0.68, 0.78, "Deadly Allure"),
    ],
    "binder_red_glare.png": [
        (0.20, 0.26, "Fiery Temper"),
        (0.44, 0.26, "Burning Prophet"),
        (0.70, 0.26, "Kindle"),
        (0.20, 0.52, "Incendiary Flow"),
        (0.44, 0.52, "Twin Bolt"),
        (0.44, 0.78, "Plasma Bolt"),
        (0.70, 0.78, "Roughshod Duo"),
    ],
}

ALIASES = {
    "putrid goblin": {"verwesender goblin", "putrid goblin", "verrottender goblin"},
    "gleaming geardrake": {
        "glänzender mechasceada",
        "glänzender mechascada",
        "gleaming geardrake",
    },
    "into the roil": {"in die turbulenz hinein", "into the roil"},
    "elder brain": {"ältestengehirn", "altestengehirn", "elder brain"},
    "burning prophet": {"feurige prophetin", "burning prophet"},
    "kindle": {"auflodern", "kindle"},
    "twin bolt": {"zwillingsblitz", "twin bolt"},
    "incendiary flow": {"flammenstrom", "incendiary flow"},
    "eldrazi horror": {"eldrazi horror", "eldrazi-schrecken"},
    "chittering host": {"chittering host"},
    "fiery temper": {"fiery temper"},
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def names_equal(pred: str, gt: str) -> bool:
    p = norm(pred).lstrip("? ").strip()
    if not p or p in {"unbekannt", "unknown"} or len(p) < 4:
        return False
    # strip DFC second face for compare
    p0 = p.split("//")[0].strip()
    g = norm(gt)
    pc = re.sub(r"[^a-z0-9äöüß]", "", p0)
    gc = re.sub(r"[^a-z0-9äöüß]", "", g)
    if p0 == g or g in p0 or (len(p0) >= 6 and p0 in g):
        return True
    if gc and len(pc) >= 5 and (gc in pc or pc in gc):
        return True
    for a in ALIASES.get(g, set()):
        ac = re.sub(r"[^a-z0-9äöüß]", "", a)
        if p0 == a or a in p0 or (ac and len(ac) >= 5 and ac in pc):
            return True
    return False


@dataclass
class CropItem:
    photo: str
    gt: str
    crop: np.ndarray
    cx: float
    cy: float


def assign_gt(
    photo: str, dets: list[dict], img: np.ndarray
) -> list[CropItem]:
    h, w = img.shape[:2]
    slots = list(GT_SLOTS[photo])
    used: set[int] = set()
    items: list[CropItem] = []
    # greedy nearest slot
    scored = []
    for i, d in enumerate(dets):
        cx = d["bbox_x"] + d["bbox_w"] / 2
        cy = d["bbox_y"] + d["bbox_h"] / 2
        for j, (sx, sy, name) in enumerate(slots):
            dist = ((cx - sx) ** 2 + (cy - sy) ** 2) ** 0.5
            scored.append((dist, i, j, name, cx, cy, d))
    scored.sort()
    taken_det: set[int] = set()
    for dist, i, j, name, cx, cy, d in scored:
        if i in taken_det or j in used:
            continue
        if dist > 0.18:
            continue
        taken_det.add(i)
        used.add(j)
        x1 = int(d["bbox_x"] * w)
        y1 = int(d["bbox_y"] * h)
        x2 = int((d["bbox_x"] + d["bbox_w"]) * w)
        y2 = int((d["bbox_y"] + d["bbox_h"]) * h)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = img[y1:y2, x1:x2].copy()
        if crop.size == 0:
            continue
        items.append(CropItem(photo, name, crop, cx, cy))
    return items


def inset(crop: np.ndarray, frac: float) -> np.ndarray:
    h, w = crop.shape[:2]
    dx, dy = int(w * frac), int(h * frac)
    if w - 2 * dx < 20 or h - 2 * dy < 20:
        return crop
    return crop[dy : h - dy, dx : w - dx].copy()


def clahe_bgr(crop: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2BGR)


def ocr_collector_band(crop: np.ndarray) -> str | None:
    """OCR bottom ~18% for collector number / set line."""
    from rapidocr_onnxruntime import RapidOCR

    h, w = crop.shape[:2]
    band = crop[int(h * 0.82) : h, :]
    if band.size == 0:
        return None
    if band.shape[1] < 200:
        band = cv2.resize(
            band, (band.shape[1] * 2, band.shape[0] * 2), interpolation=cv2.INTER_CUBIC
        )
    tmp = OUT / "_coll_ocr.jpg"
    cv2.imwrite(str(tmp), band)
    try:
        result, _ = RapidOCR()(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)
    if not result:
        return None
    return " ".join(str(line[1]) for line in result if len(line) > 1).strip() or None


def extract_collector_token(text: str) -> str | None:
    if not text:
        return None
    # common patterns: "116", "116a", "SOI 116"
    m = re.search(r"\b(\d{1,4}[a-zA-Z]?)\b", text)
    return m.group(1) if m else None


def milo_top_k(milo, crop: np.ndarray, k: int = 3) -> list[tuple[str, float, dict | None]]:
    """Rotate, take best angle's top-k search hits."""
    from magic_optimizer.vision.identify import rotate_image, _scryfall_by_id
    from magic_optimizer.vision.scryfall import lookup_card_name

    crop = _ensure_crop(crop)
    best_hits: list[tuple[str, float]] = []
    best_score = -1.0
    for angle in (0, 90, 180, 270):
        view = rotate_image(crop, angle)
        try:
            warped = milo.dewarp(view)
            emb = milo.catalog.embedder.embed(np.ascontiguousarray(warped))
            hits = milo.catalog.search(emb, top_k=k)
        except ValueError:
            try:
                emb = milo.catalog.embedder.embed(np.ascontiguousarray(view))
                hits = milo.catalog.search(emb, top_k=k)
            except ValueError:
                continue
        if not hits:
            continue
        if float(hits[0][0]) > best_score:
            best_score = float(hits[0][0])
            best_hits = [(cid, float(sc)) for sc, cid in hits]
    out = []
    for card_id, score in best_hits:
        if card_id not in milo._name:
            meta = _scryfall_by_id(card_id)
            milo._name[card_id] = meta["card_name"] if meta else str(card_id)
            meta_r = meta
        else:
            meta_r = lookup_card_name(milo._name[card_id])
        out.append((milo._name[card_id], score, meta_r))
    return out


def _ensure_crop(crop: np.ndarray) -> np.ndarray:
    """Contiguous BGR uint8, min size for Milo embedder."""
    out = np.ascontiguousarray(crop)
    if out.dtype != np.uint8:
        out = np.clip(out, 0, 255).astype(np.uint8)
    h, w = out.shape[:2]
    if h < 64 or w < 48:
        scale = max(64 / max(h, 1), 48 / max(w, 1))
        out = cv2.resize(
            out,
            (max(48, int(w * scale)), max(64, int(h * scale))),
            interpolation=cv2.INTER_CUBIC,
        )
    return out


def method_baseline_s3(crop, milo):
    from magic_optimizer.vision.identify import identify_crop_s3

    try:
        return identify_crop_s3(_ensure_crop(crop), milo=milo)
    except ValueError:
        # Milo embedder sometimes chokes on dewarped views; retry without crashing ablation
        from magic_optimizer.vision.identify import IdPred

        return IdPred("Unbekannt", 0.0, "error", uncertain=True)


def method_inset8(crop, milo):
    return method_baseline_s3(inset(crop, 0.08), milo)


def method_inset12(crop, milo):
    return method_baseline_s3(inset(crop, 0.12), milo)


def method_clahe(crop, milo):
    return method_baseline_s3(clahe_bgr(crop), milo)


def method_best_preprocess(crop, milo):
    from magic_optimizer.vision.identify import identify_rotations, hybrid_ocr, gate, IdPred

    candidates = [
        _ensure_crop(crop),
        _ensure_crop(inset(crop, 0.08)),
        _ensure_crop(clahe_bgr(crop)),
        _ensure_crop(inset(clahe_bgr(crop), 0.08)),
    ]
    best = None
    for c in candidates:
        try:
            rot = identify_rotations(c, milo)
        except ValueError:
            continue
        if best is None or rot.score > best[0].score:
            best = (rot, c)
    if best is None:
        return IdPred("Unbekannt", 0.0, "error", uncertain=True)
    return gate(hybrid_ocr(best[1], best[0]))


def method_collector_tiebreak(crop, milo):
    from magic_optimizer.vision.identify import hybrid_ocr, gate, IdPred
    from magic_optimizer.vision.scryfall import lookup_card_name, scryfall_get

    tops = milo_top_k(milo, crop, k=3)
    if not tops:
        return method_baseline_s3(crop, milo)
    base = IdPred(tops[0][0], tops[0][1], "milo_top", meta=tops[0][2])
    # only intervene when top-2 close
    if len(tops) >= 2 and abs(tops[0][1] - tops[1][1]) < 0.08:
        raw = ocr_collector_band(crop)
        tok = extract_collector_token(raw or "")
        if tok:
            # try each top candidate: fuzzy name + collector via scryfall search
            for name, score, meta in tops:
                # scryfall: name + number
                try:
                    r = scryfall_get(
                        "https://api.scryfall.com/cards/named",
                        params={"fuzzy": name},
                        timeout=8,
                    )
                    time.sleep(0.05)
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    cn = str(data.get("collector_number") or "")
                    if cn.lower() == tok.lower() or tok.lower() in cn.lower():
                        meta2 = {
                            "card_name": data.get("name"),
                            "set_code": (data.get("set") or "").upper() or None,
                            "collector_number": cn,
                            "scryfall_id": data.get("id"),
                        }
                        return gate(
                            hybrid_ocr(
                                crop,
                                IdPred(meta2["card_name"], max(score, 0.75), "collector_tb", meta=meta2),
                            )
                        )
                except Exception:
                    continue
            # also try searching set:number style if OCR has letters+digits
            q = raw.strip() if raw else tok
            try:
                r = scryfall_get(
                    "https://api.scryfall.com/cards/search",
                    params={"q": f"number:{tok}", "unique": "prints"},
                    timeout=8,
                )
                time.sleep(0.05)
                # too broad — skip
            except Exception:
                pass
    return gate(hybrid_ocr(crop, base))


def method_top3_ocr_rerank(crop, milo):
    from magic_optimizer.vision.identify import (
        hybrid_ocr,
        gate,
        IdPred,
        ocr_title_from_crop,
    )
    from magic_optimizer.vision.scryfall import lookup_card_name

    tops = milo_top_k(milo, crop, k=3)
    if not tops:
        return method_baseline_s3(crop, milo)
    title = ocr_title_from_crop(crop)
    ocr_meta = lookup_card_name(title) if title and len(title) >= 5 else None
    if ocr_meta:
        ocr_name = norm(ocr_meta["card_name"])
        for name, score, meta in tops:
            if names_equal(name, ocr_meta["card_name"]) or norm(name) == ocr_name:
                return gate(
                    IdPred(ocr_meta["card_name"], max(score, 0.8), "top3_ocr", meta=ocr_meta)
                )
        # OCR resolved but disagrees with all top3 → use OCR if milo top weak
        if tops[0][1] < 0.65:
            return gate(IdPred(ocr_meta["card_name"], 0.85, "ocr_override", meta=ocr_meta))
    base = IdPred(tops[0][0], tops[0][1], "milo_top", meta=tops[0][2])
    return gate(hybrid_ocr(crop, base))


METHODS: dict[str, Callable] = {
    "S3_baseline": method_baseline_s3,
    "A1_inset8": method_inset8,
    "A1_inset12": method_inset12,
    "A2_clahe": method_clahe,
    "A3_best_preprocess": method_best_preprocess,
    "B1_collector_tiebreak": method_collector_tiebreak,
    "B2_top3_ocr_rerank": method_top3_ocr_rerank,
}


def eval_method(name: str, items: list[CropItem], milo) -> dict[str, Any]:
    hits = 0
    auto_hits = 0
    auto_n = 0
    uncertain = 0
    details = []
    fn = METHODS[name]
    for it in items:
        pred = fn(it.crop, milo)
        hit = names_equal(pred.name, it.gt)
        if hit:
            hits += 1
        if pred.uncertain:
            uncertain += 1
        else:
            auto_n += 1
            if hit:
                auto_hits += 1
        details.append(
            {
                "photo": it.photo,
                "gt": it.gt,
                "pred": pred.name,
                "score": pred.score,
                "source": pred.source,
                "uncertain": pred.uncertain,
                "hit": hit,
            }
        )
    n = len(items)
    return {
        "method": name,
        "n": n,
        "raw_hits": hits,
        "raw_pct": round(100 * hits / n, 1) if n else 0,
        "auto_n": auto_n,
        "auto_hits": auto_hits,
        "auto_precision_pct": round(100 * auto_hits / auto_n, 1) if auto_n else 0,
        "coverage_pct": round(100 * auto_n / n, 1) if n else 0,
        "uncertain": uncertain,
        "delta_raw_vs_baseline": None,
        "details": details,
    }


def main() -> None:
    from magic_optimizer.vision.binder_grid import detect_binder_slots
    from magic_optimizer.vision.identify import get_milo_engine, MiloEngine
    import magic_optimizer.vision.identify as identify_mod

    identify_mod._MILO = None
    identify_mod._MILO_TRIED = False
    print("Loading Milo…")
    milo = get_milo_engine()
    if milo is None:
        raise SystemExit("Milo unavailable")

    real = ROOT / "tests/fixtures/scan/real"
    items: list[CropItem] = []
    for photo in GT_SLOTS:
        path = real / photo
        img = cv2.imread(str(path))
        dets = detect_binder_slots(str(path))
        assigned = assign_gt(photo, dets, img)
        print(f"{photo}: {len(dets)} dets → {len(assigned)} GT-matched")
        for a in assigned:
            print(f"  ({a.cx:.2f},{a.cy:.2f}) → {a.gt}")
        items.extend(assigned)

    print(f"\nTotal matched crops: {len(items)}")
    results = []
    baseline_hits = None
    for mname in METHODS:
        print(f"\n=== {mname} ===")
        t0 = time.time()
        res = eval_method(mname, items, milo)
        if mname == "S3_baseline":
            baseline_hits = res["raw_hits"]
        else:
            res["delta_raw_vs_baseline"] = res["raw_hits"] - (baseline_hits or 0)
        dt = time.time() - t0
        res["seconds"] = round(dt, 1)
        print(
            f"  raw {res['raw_hits']}/{res['n']} ({res['raw_pct']}%)  "
            f"auto_prec {res['auto_precision_pct']}%  cov {res['coverage_pct']}%  "
            f"unc {res['uncertain']}  Δraw={res['delta_raw_vs_baseline']}  ({dt:.0f}s)"
        )
        # drop bulky details from summary print but keep in JSON
        results.append(res)

    # misses for baseline vs best
    base = next(r for r in results if r["method"] == "S3_baseline")
    print("\n======== SUMMARY ========")
    print(f"{'method':28} raw%   Δhit  auto_prec  cov%  unc")
    for r in results:
        d = r["delta_raw_vs_baseline"]
        d_s = f"{d:+d}" if d is not None else "  0"
        print(
            f"{r['method']:28} {r['raw_pct']:5.1f}  {d_s:>4}  "
            f"{r['auto_precision_pct']:7.1f}  {r['coverage_pct']:5.1f}  {r['uncertain']}"
        )

    # recommend: raw_hits improved OR (same raw and better auto_precision without cov drop >5)
    winners = []
    for r in results:
        if r["method"] == "S3_baseline":
            continue
        d = r["delta_raw_vs_baseline"] or 0
        prec_gain = r["auto_precision_pct"] - base["auto_precision_pct"]
        cov_drop = base["coverage_pct"] - r["coverage_pct"]
        if d > 0 and cov_drop <= 5:
            winners.append(r["method"])
        elif d == 0 and prec_gain >= 3 and cov_drop <= 5:
            winners.append(r["method"])

    print("\nWinners (ship candidates):", winners or "NONE — keep S3 baseline")

    payload = {
        "n_crops": len(items),
        "gt_slots": {k: [(a, b, c) for a, b, c in v] for k, v in GT_SLOTS.items()},
        "results": results,
        "winners": winners,
        "ship_rule": "delta_raw>0 & cov_drop<=5 OR (delta_raw==0 & prec_gain>=3 & cov_drop<=5)",
    }
    out = OUT / "ablation_results.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
