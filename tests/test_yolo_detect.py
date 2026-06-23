"""Tests for YOLO detector wrapper."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock


def _load_yolo():
    path = Path(__file__).resolve().parents[1] / "src/magic_optimizer/vision/yolo.py"
    spec = importlib.util.spec_from_file_location("vision_yolo", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_detect_with_yolo_no_model(monkeypatch, tmp_path):
    yolo = _load_yolo()
    monkeypatch.setattr(yolo, "DEFAULT_MODEL", str(tmp_path / "missing.pt"))
    monkeypatch.setattr(yolo, "_model", None)
    assert yolo.detect_with_yolo(str(tmp_path / "img.jpg")) == []


def test_detect_with_yolo_parses_boxes(monkeypatch, tmp_path):
    yolo = _load_yolo()
    fake_pt = tmp_path / "best.pt"
    fake_pt.write_bytes(b"stub")
    img = tmp_path / "img.jpg"
    img.write_bytes(b"x")

    box = MagicMock()
    box.xyxy = [MagicMock()]
    box.xyxy[0].tolist.return_value = [10, 20, 110, 220]
    box.conf = [MagicMock()]
    box.conf[0] = 0.88

    result = MagicMock()
    result.orig_shape = (400, 200)
    result.boxes = [box]

    mock_model = MagicMock()
    mock_model.predict.return_value = [result]

    monkeypatch.setattr(yolo, "DEFAULT_MODEL", str(fake_pt))
    monkeypatch.setattr(yolo, "_model", None)

    fake_ultra = MagicMock()
    fake_ultra.YOLO.return_value = mock_model
    monkeypatch.setitem(__import__("sys").modules, "ultralytics", fake_ultra)
    dets = yolo.detect_with_yolo(str(img))

    assert len(dets) == 1
    assert dets[0]["source"] == "yolo"
    assert dets[0]["bbox_x"] == 0.05
    assert dets[0]["confidence"] == 0.88


def test_model_available_false_when_missing(monkeypatch, tmp_path):
    yolo = _load_yolo()
    monkeypatch.setattr(yolo, "DEFAULT_MODEL", str(tmp_path / "missing.pt"))
    assert yolo.model_available() is False
