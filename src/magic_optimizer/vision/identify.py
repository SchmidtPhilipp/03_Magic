"""Card identification — S3: Milo rotation voting + OCR hybrid + confidence gate."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

CONF_AUTO = 0.50
OCR_MIN_LEN = 5
OCR_OVERRIDE_BELOW = 0.75
OCR_CONFIRM_FLOOR = 0.78
_MILO: Any = None
_MILO_TRIED = False

# Catalog / Milo matches that are almost never real binder cards.
_JUNK_EXACT = frozenset(
    {
        "blank card",
        "treasure",
        "food",
        "clue",
        "blood",
        "powerstone",
        "junk",
        "card",
    }
)


@dataclass
class IdPred:
    name: str
    score: float
    source: str
    uncertain: bool = False
    meta: dict[str, Any] | None = field(default=None)


def rotate_image(img: np.ndarray, angle: int) -> np.ndarray:
    if cv2 is None or angle % 360 == 0:
        return img
    if angle % 360 == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if angle % 360 == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle % 360 == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), borderValue=(24, 28, 32))


def clean_ocr_title(raw: str) -> str:
    """Strip collector crumbs / trailing noise so Scryfall fuzzy can resolve DE titles."""
    t = (raw or "").strip()
    if not t:
        return ""
    # Leading set symbol / collector number crumbs: "48 Vampir-…" / "B 12 Title"
    t = re.sub(r"^[\W_\d]+", "", t)
    t = re.sub(r"^\d{1,4}\s+", "", t)
    # Trailing pocket noise: "Title 29" / "Title 2?" / "Title 2@" / CJK junk
    t = re.sub(r"\s+[\d@?]+[\W\d]*$", "", t)
    t = re.sub(r"[\u4e00-\u9fff]+", " ", t)
    # Dots often glue German words: Backe.backeKuchen
    t = t.replace(".", " ")
    # Split glued CamelCase tokens: FatChocobo → Fat Chocobo, diePlanke → die Planke
    t = re.sub(r"(?<=[a-zäöüß])(?=[A-ZÄÖÜ])", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _ocr_query_variants(cleaned: str) -> list[str]:
    """Generate light OCR repair variants for Scryfall fuzzy."""
    seen: set[str] = set()
    out: list[str] = []

    def add(s: str) -> None:
        s = re.sub(r"\s+", " ", (s or "").strip())
        if len(s) >= OCR_MIN_LEN and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)

    low = cleaned.lower()
    # Priority: known DE titles that Scryfall fuzzy mis-resolves from raw OCR
    if "umdrehen" in low or "spieß" in low or "spiess" in low:
        add("Turn the Tables")
    if "narset" in low:
        add("Narset's Rebuke")
        add("Narsets Rebuke")

    add(cleaned)
    # Common DE OCR confusions (ü/ä + endings)
    repaired = cleaned
    repairs = (
        ("tiber", "uber"),
        ("Tiber", "Uber"),
        ("gchen", "gehen"),
        ("moniage", "montage"),
        ("Summoht", "Summon"),
        ("Tasisur", "Tasigur"),
        ("Cruelry", "Cruelty"),
        ("Bregclang", "Rebuke"),
        ("MaBregclang", "Rebuke"),
        ("Ma Bregclang", "Rebuke"),
    )
    for a, b in repairs:
        if a in repaired:
            repaired = repaired.replace(a, b)
    add(repaired)
    add(repaired.replace("uber", "über").replace("Uber", "Über"))
    # Drop short garbage tokens / try compact windows (OCR often appends junk)
    for base in (cleaned, repaired):
        toks = [t for t in base.split() if len(t) >= 3]
        if len(toks) >= 2:
            add(" ".join(toks))
        for n in (2, 3, 4):
            if len(toks) >= n:
                add(" ".join(toks[:n]))
                add(" ".join(toks[-n:]))
        # Long final token alone (DE compounds often unique enough for fuzzy)
        if toks and len(toks[-1]) >= 10:
            add(toks[-1])
        # Hyphenated compounds: try ß/ss and f/ß confusions lightly
        for tok in toks:
            if "-" in tok and len(tok) >= 10:
                add(tok)
                add(tok.replace("strafen", "straßen").replace("streifen", "straßen"))
    return out


def normalize_card_name(name: str) -> str:
    """Collapse identical DFC faces: 'X // X' → 'X'."""
    n = (name or "").strip()
    if " // " not in n:
        return n
    left, right = n.split(" // ", 1)
    if left.strip().lower() == right.strip().lower():
        return left.strip()
    return n


def is_junk_match(name: str) -> bool:
    """True for tokens, blank cards, unresolved UUID backs, etc."""
    n = normalize_card_name(name).strip().lower()
    if not n or n in {"unbekannt", "unknown"}:
        return True
    if n in _JUNK_EXACT:
        return True
    if "double-faced substitute" in n:
        return True
    if n.endswith("_back"):
        return True
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f-]{27}(_back)?", n):
        return True
    # Bare creature-type / emblem tokens often returned without a real card face
    if n in {
        "zombie",
        "soldier",
        "goblin",
        "spirit",
        "saproling",
        "thopter",
        "insect",
        "beast",
        "dragon",
        "elemental",
        "warrior",
        "knight",
        "angel",
        "demon",
        "elf",
        "merfolk",
        "vampire",
        "wizard",
        "germ",
        "treasure",
        "food",
        "clue",
        "blood",
    }:
        return True
    return False


def gate(pred: IdPred, thresh: float = CONF_AUTO) -> IdPred:
    """Mark low-confidence Milo hits uncertain; OCR stays trusted."""
    if pred.source == "ocr" or pred.source.endswith("+ocr"):
        return pred
    if is_junk_match(pred.name):
        return IdPred(pred.name, pred.score, pred.source, uncertain=True, meta=pred.meta)
    if pred.score < thresh:
        return IdPred(pred.name, pred.score, pred.source, uncertain=True, meta=pred.meta)
    return pred


def ocr_title_from_crop(crop_bgr: np.ndarray) -> str | None:
    """OCR the title band of a card crop (tries a few band heights)."""
    if cv2 is None:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None

    h, w = crop_bgr.shape[:2]
    engine = RapidOCR()
    best: str | None = None
    for frac in (0.22, 0.28):
        title = crop_bgr[0 : max(int(h * frac), 12), :]
        if title.size == 0:
            continue
        view = title
        if view.shape[1] < 220:
            view = cv2.resize(
                view,
                (view.shape[1] * 2, view.shape[0] * 2),
                interpolation=cv2.INTER_CUBIC,
            )
        tmp = Path("/tmp") / "_magic_ocr_title.jpg"
        cv2.imwrite(str(tmp), view)
        try:
            result, _ = engine(str(tmp))
        finally:
            tmp.unlink(missing_ok=True)
        if not result:
            continue
        text = " ".join(str(line[1]) for line in result if len(line) > 1).strip()
        if text and (best is None or len(text) > len(best)):
            best = text
    return best


def _resolve_ocr_title(raw: str | None) -> dict[str, Any] | None:
    from magic_optimizer.vision.scryfall import lookup_card_name

    if not raw:
        return None
    cleaned = clean_ocr_title(raw)
    if len(cleaned) < OCR_MIN_LEN:
        return None
    letters = sum(c.isalpha() for c in cleaned)
    if letters < 4:
        return None
    for query in _ocr_query_variants(cleaned):
        meta = lookup_card_name(query)
        if meta:
            return meta
        alt = re.sub(r"[^\w\s]", " ", query, flags=re.UNICODE)
        alt = re.sub(r"\s+", " ", alt).strip()
        if alt != query and len(alt) >= OCR_MIN_LEN:
            meta = lookup_card_name(alt)
            if meta:
                return meta
    return None


def hybrid_ocr(crop: np.ndarray, milo_pred: IdPred) -> IdPred:
    """Prefer Scryfall-resolved OCR when Milo is weak, junk, or OCR confirms."""
    milo_pred = IdPred(
        normalize_card_name(milo_pred.name),
        milo_pred.score,
        milo_pred.source,
        milo_pred.uncertain,
        milo_pred.meta,
    )
    raw = ocr_title_from_crop(crop)
    meta = _resolve_ocr_title(raw)
    if not meta:
        if is_junk_match(milo_pred.name):
            return IdPred(milo_pred.name, milo_pred.score, milo_pred.source, uncertain=True, meta=milo_pred.meta)
        return milo_pred

    ocr_pred = IdPred(meta["card_name"], 0.85, "ocr", meta=meta)
    milo_name = (milo_pred.name or "").strip().lower()
    ocr_name = (meta.get("card_name") or "").strip().lower()
    same = milo_name == ocr_name or (
        milo_pred.meta
        and meta.get("scryfall_id")
        and milo_pred.meta.get("scryfall_id") == meta.get("scryfall_id")
    )

    if is_junk_match(milo_pred.name):
        return ocr_pred
    if same:
        # OCR confirms Milo (incl. DE printed title → EN oracle) → auto-trust
        return IdPred(
            meta["card_name"],
            max(float(milo_pred.score), OCR_CONFIRM_FLOOR),
            f"{milo_pred.source}+ocr",
            meta=meta,
        )
    if milo_pred.score < OCR_OVERRIDE_BELOW:
        return ocr_pred
    return milo_pred


def identify_rotations(crop: np.ndarray, milo: Any) -> IdPred:
    """Try 0/90/180/270 and keep the highest Milo score."""
    best = IdPred("Unbekannt", -1.0, "milo_rot")
    best_angle = 0
    for angle in (0, 90, 180, 270):
        view = rotate_image(crop, angle)
        pred = milo.identify_one(view)
        if pred.score > best.score:
            best = pred
            best_angle = angle
    if best.score < 0:
        return IdPred("Unbekannt", 0.0, "milo_rot")
    return IdPred(best.name, best.score, f"milo_rot{best_angle}", meta=best.meta)


def clahe_bgr(crop: np.ndarray) -> np.ndarray:
    """Local contrast boost (ablation A2: +1 raw hit on binder set, low cost)."""
    if cv2 is None or crop.size == 0:
        return crop
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l2 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2BGR)


def identify_crop_s3(crop: np.ndarray, milo: Any | None = None) -> IdPred:
    """Full S3 pipeline on one crop (CLAHE → rotations → OCR hybrid → gate)."""
    engine = milo if milo is not None else get_milo_engine()
    crop_p = clahe_bgr(crop)
    if engine is None:
        # OCR-only fallback path for a single crop
        from magic_optimizer.vision.scryfall import lookup_card_name

        raw = ocr_title_from_crop(crop_p)
        if not raw:
            return IdPred("Unbekannt", 0.0, "none", uncertain=True)
        meta = lookup_card_name(raw)
        if meta:
            return IdPred(meta["card_name"], 0.85, "ocr", meta=meta)
        return IdPred(raw, 0.45, "ocr_raw", uncertain=True)

    rot = identify_rotations(crop_p, engine)
    return gate(hybrid_ocr(crop_p, rot))


class MiloEngine:
    """CollectorVision Milo catalog matcher with optional corner dewarp."""

    def __init__(self) -> None:
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

    def identify_one(self, crop: np.ndarray) -> IdPred:
        from magic_optimizer.vision.scryfall import lookup_card_name
        from PIL import Image

        warped = self.dewarp(crop)
        if isinstance(warped, np.ndarray):
            if warped.size == 0:
                return IdPred("Unbekannt", 0.0, "milo")
            rgb = cv2.cvtColor(np.ascontiguousarray(warped), cv2.COLOR_BGR2RGB)
            warped = Image.fromarray(rgb)
        try:
            emb = self.catalog.embedder.embed(warped)
        except ValueError:
            return IdPred("Unbekannt", 0.0, "milo")
        hits = self.catalog.search(emb, top_k=5)
        if not hits:
            return IdPred("Unbekannt", 0.0, "milo")
        chosen: IdPred | None = None
        for score, card_id in hits:
            score_f = float(score)
            if card_id not in self._name:
                meta = _scryfall_by_id(card_id)
                self._name[card_id] = meta["card_name"] if meta else str(card_id)
                pred_meta = meta
            else:
                pred_meta = lookup_card_name(self._name[card_id])
            name = normalize_card_name(self._name[card_id])
            pred = IdPred(name, score_f, "milo", meta=pred_meta)
            if not is_junk_match(name):
                return pred
            if chosen is None:
                chosen = pred
        return chosen or IdPred("Unbekannt", 0.0, "milo")


def _scryfall_by_id(card_id: str) -> dict[str, Any] | None:
    from magic_optimizer.vision.scryfall import scryfall_get

    try:
        r = scryfall_get(f"https://api.scryfall.com/cards/{card_id}", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        uris = data.get("image_uris") or {}
        faces = data.get("card_faces") or []
        image_uri = uris.get("small")
        if not image_uri and faces:
            image_uri = (faces[0].get("image_uris") or {}).get("small")
        return {
            "scryfall_id": data.get("id"),
            "card_name": data.get("name"),
            "set_code": (data.get("set") or "").upper() or None,
            "collector_number": str(data.get("collector_number") or "") or None,
            "image_uri": image_uri,
        }
    except Exception:
        return None


def get_milo_engine() -> Any | None:
    global _MILO, _MILO_TRIED
    if _MILO is not None:
        return _MILO
    if _MILO_TRIED:
        return None
    _MILO_TRIED = True
    try:
        _MILO = MiloEngine()
        return _MILO
    except Exception:
        return None


def _crop_from_det(img: np.ndarray, det: dict[str, Any]) -> np.ndarray | None:
    h, w = img.shape[:2]
    x1 = int(det["bbox_x"] * w)
    y1 = int(det["bbox_y"] * h)
    x2 = int((det["bbox_x"] + det["bbox_w"]) * w)
    y2 = int((det["bbox_y"] + det["bbox_h"]) * h)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 20 or y2 - y1 < 20:
        return None
    return img[y1:y2, x1:x2].copy()


def _apply_pred(det: dict[str, Any], pred: IdPred) -> dict[str, Any]:
    out = dict(det)
    out["detected_name"] = pred.name
    out["confidence"] = float(pred.score)
    out["id_source"] = pred.source
    out["uncertain"] = bool(pred.uncertain)
    if pred.uncertain:
        out["status"] = "pending"
    meta = pred.meta
    if not meta and pred.name and pred.name.lower() not in {"unbekannt", "unknown"}:
        from magic_optimizer.vision.scryfall import lookup_card_name

        meta = lookup_card_name(pred.name)
        pred = IdPred(pred.name, pred.score, pred.source, pred.uncertain, meta)
    if meta:
        out["detected_name"] = normalize_card_name(
            meta.get("card_name") or out["detected_name"]
        )
        out["set_code"] = meta.get("set_code")
        out["collector_number"] = meta.get("collector_number")
        out["scryfall_id"] = meta.get("scryfall_id")
        out["image_uri"] = meta.get("image_uri")
    return out


def enrich_detections_with_identify(
    image_path: str, detections: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Identify each detection with S3 (Milo rotations + OCR hybrid + gate).

    Falls back to OCR-only enrichment when Milo is unavailable.
    """
    milo = get_milo_engine()
    if milo is None:
        from magic_optimizer.vision.ocr import enrich_detections_with_ocr

        return enrich_detections_with_ocr(image_path, detections)

    if cv2 is None:
        return detections
    img = cv2.imread(image_path)
    if img is None:
        return detections

    out: list[dict[str, Any]] = []
    for det in detections:
        crop = _crop_from_det(img, det)
        if crop is None:
            out.append(det)
            continue
        pred = identify_crop_s3(crop, milo=milo)
        out.append(_apply_pred(det, pred))
    return out
