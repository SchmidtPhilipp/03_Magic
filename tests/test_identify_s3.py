"""S3 identify: rotation voting + OCR hybrid + confidence gate."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from magic_optimizer.vision import identify


@dataclass
class FakePred:
    name: str
    score: float
    source: str = "milo"
    uncertain: bool = False


def test_clahe_bgr_changes_pixels():
    img = np.zeros((64, 48, 3), dtype=np.uint8)
    img[8:56, 8:40] = 40
    img[20:40, 16:32] = 180
    out = identify.clahe_bgr(img)
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    assert not np.array_equal(out, img)


def test_identify_crop_s3_runs_clahe_before_milo():
    crop = np.zeros((80, 60, 3), dtype=np.uint8)
    crop[10:70, 10:50] = 50

    class FakeMilo:
        def identify_one(self, view):
            return identify.IdPred("Fiery Temper", 0.72, "milo")

    with patch.object(identify, "clahe_bgr", wraps=identify.clahe_bgr) as clahe_spy, patch.object(
        identify, "ocr_title_from_crop", return_value=None
    ):
        out = identify.identify_crop_s3(crop, milo=FakeMilo())
    assert clahe_spy.called
    assert out.name == "Fiery Temper"



def test_gate_marks_low_milo_score_uncertain():
    pred = identify.IdPred(name="Lightning Bolt", score=0.40, source="milo_rot0")
    gated = identify.gate(pred, thresh=0.55)
    assert gated.uncertain is True
    assert gated.name == "Lightning Bolt"


def test_gate_keeps_ocr_even_if_below_thresh():
    pred = identify.IdPred(name="Village Rites", score=0.85, source="ocr")
    # OCR uses fixed score; gate should not mark OCR uncertain by score alone
    gated = identify.gate(identify.IdPred("X", 0.40, "ocr"), thresh=0.55)
    assert gated.uncertain is False


def test_clean_ocr_title_strips_collector_noise():
    assert identify.clean_ocr_title("48 Vampir-Seelenrufer") == "Vampir-Seelenrufer"
    assert identify.clean_ocr_title("Abstechen 29") == "Abstechen"
    assert identify.clean_ocr_title("Galvanisieren") == "Galvanisieren"
    assert identify.clean_ocr_title("Backe.backeKuchen") == "Backe backe Kuchen"
    assert "Fat Chocobo" in identify.clean_ocr_title("Summoht FatChocobo")


def test_resolve_ocr_variants_fix_german_typos():
    with patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        side_effect=lambda q: (
            {"card_name": "Walk the Plank"}
            if "uber die Planke gehen" in q.lower()
            or "über die planke gehen" in q.lower()
            else None
        ),
    ):
        meta = identify._resolve_ocr_title("tiber diePlanke gchen")
    assert meta and meta["card_name"] == "Walk the Plank"


def test_resolve_prefers_turn_the_tables_for_spiess_ocr():
    with patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        side_effect=lambda q: (
            {"card_name": "Turn the Tables"}
            if q == "Turn the Tables"
            else {"card_name": "Skewer the Critics"}
            if "Spieß" in q or "Spiess" in q
            else None
        ),
    ):
        meta = identify._resolve_ocr_title("Den Spieß umdrehen")
    assert meta and meta["card_name"] == "Turn the Tables"


def test_is_junk_match_flags_tokens_and_backs():
    assert identify.is_junk_match("Blank Card")
    assert identify.is_junk_match("Treasure")
    assert identify.is_junk_match("70bbfec6-1e35-4fde-adc5-ed15f8997ce4_back")
    assert not identify.is_junk_match("Vampire Soulcaller")


def test_hybrid_uses_ocr_when_milo_weak():
    crop = np.zeros((100, 70, 3), dtype=np.uint8)
    milo = identify.IdPred("Wrong Card", 0.45, "milo")
    with patch.object(identify, "ocr_title_from_crop", return_value="Village Rites"), patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        return_value={
            "card_name": "Village Rites",
            "set_code": "M21",
            "collector_number": "1",
            "scryfall_id": "abc",
            "image_uri": "https://example.com/v.jpg",
        },
    ):
        out = identify.hybrid_ocr(crop, milo)
    assert out.name == "Village Rites"
    assert out.source == "ocr"
    assert out.meta and out.meta["set_code"] == "M21"


def test_hybrid_overrides_junk_milo_even_if_strong():
    crop = np.zeros((100, 70, 3), dtype=np.uint8)
    milo = identify.IdPred("Blank Card", 0.91, "milo")
    with patch.object(identify, "ocr_title_from_crop", return_value="Village Rites"), patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        return_value={"card_name": "Village Rites", "set_code": "M21"},
    ):
        out = identify.hybrid_ocr(crop, milo)
    assert out.name == "Village Rites"
    assert out.source == "ocr"


def test_hybrid_boosts_when_ocr_confirms_milo():
    crop = np.zeros((100, 70, 3), dtype=np.uint8)
    milo = identify.IdPred("Vampire Soulcaller", 0.58, "milo_rot180")
    with patch.object(
        identify, "ocr_title_from_crop", return_value="48 Vampir-Seelenrufer"
    ), patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        return_value={
            "card_name": "Vampire Soulcaller",
            "scryfall_id": "vs",
            "set_code": "FDN",
        },
    ):
        out = identify.hybrid_ocr(crop, milo)
    assert out.name == "Vampire Soulcaller"
    assert out.uncertain is False
    assert out.score >= 0.78
    assert "ocr" in out.source


def test_hybrid_keeps_strong_milo():
    crop = np.zeros((100, 70, 3), dtype=np.uint8)
    milo = identify.IdPred("Roughshod Duo", 0.82, "milo_rot90")
    with patch.object(identify, "ocr_title_from_crop", return_value="Roughshod Duo"), patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        return_value={"card_name": "Roughshod Duo", "set_code": "BLB"},
    ):
        out = identify.hybrid_ocr(crop, milo)
    assert out.name == "Roughshod Duo"
    assert out.source.startswith("milo")


def test_identify_rotations_picks_best_score():
    crop = np.zeros((80, 60, 3), dtype=np.uint8)

    class FakeMilo:
        def identify_one(self, view):
            # taller after 90° rotate → pretend better match
            if view.shape[0] < view.shape[1]:
                return identify.IdPred("Siege Zombie", 0.71, "milo")
            return identify.IdPred("Wrong", 0.40, "milo")

    out = identify.identify_rotations(crop, FakeMilo())
    assert out.name == "Siege Zombie"
    assert out.score == pytest.approx(0.71)
    assert "rot" in out.source


def test_identify_crop_s3_applies_gate_after_hybrid():
    crop = np.zeros((80, 60, 3), dtype=np.uint8)

    class FakeMilo:
        def identify_one(self, view):
            return identify.IdPred("Mystery", 0.42, "milo")

    with patch.object(identify, "ocr_title_from_crop", return_value=None):
        out = identify.identify_crop_s3(crop, milo=FakeMilo())
    assert out.uncertain is True
    assert out.name == "Mystery"


def test_enrich_detections_writes_name_and_uncertain_flag(tmp_path):
    import cv2

    img = np.full((200, 140, 3), 40, dtype=np.uint8)
    path = tmp_path / "card.jpg"
    cv2.imwrite(str(path), img)

    det = {
        "bbox_x": 0.1,
        "bbox_y": 0.1,
        "bbox_w": 0.8,
        "bbox_h": 0.8,
        "detected_name": "Unbekannt",
        "confidence": 0.5,
        "status": "pending",
    }

    class FakeMilo:
        def identify_one(self, view):
            return identify.IdPred("Fiery Temper", 0.78, "milo")

    with patch.object(identify, "get_milo_engine", return_value=FakeMilo()), patch.object(
        identify, "ocr_title_from_crop", return_value=None
    ), patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        return_value={
            "card_name": "Fiery Temper",
            "set_code": "SOI",
            "collector_number": "116",
            "scryfall_id": "ft",
            "image_uri": "https://example.com/ft.jpg",
        },
    ):
        out = identify.enrich_detections_with_identify(str(path), [det])

    assert out[0]["detected_name"] == "Fiery Temper"
    assert out[0]["uncertain"] is False
    assert out[0]["id_source"].startswith("milo")
    assert out[0]["set_code"] == "SOI"
    assert float(out[0]["confidence"]) >= 0.78


def test_enrich_falls_back_to_ocr_when_milo_unavailable(tmp_path):
    import cv2

    img = np.full((200, 140, 3), 40, dtype=np.uint8)
    path = tmp_path / "card.jpg"
    cv2.imwrite(str(path), img)
    det = {
        "bbox_x": 0.1,
        "bbox_y": 0.1,
        "bbox_w": 0.8,
        "bbox_h": 0.8,
        "detected_name": "Unbekannt",
        "confidence": 0.5,
        "status": "pending",
    }
    with patch.object(identify, "get_milo_engine", return_value=None), patch(
        "magic_optimizer.vision.ocr.enrich_detections_with_ocr",
        side_effect=lambda p, dets: [
            {**dets[0], "detected_name": "OCR Only", "confidence": 0.55}
        ],
    ):
        out = identify.enrich_detections_with_identify(str(path), [det])
    assert out[0]["detected_name"] == "OCR Only"
