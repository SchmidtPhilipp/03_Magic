"""Binder grid occupancy / NMS hardening."""

from __future__ import annotations

import numpy as np

from magic_optimizer.vision import binder_grid as bg


def test_gap_threshold_ignores_high_outlier():
    """One saturated cell must not raise thresh above real cards (~0.7)."""
    scores = [0.61, 0.67, 0.70, 0.73, 0.73, 0.75, 0.75, 0.82, 1.0]
    thresh = bg.occupancy_threshold(scores)
    assert thresh <= 0.55
    assert all(s >= thresh for s in scores if s >= 0.61)


def test_gap_threshold_separates_empty_pocket():
    scores = [0.30, 0.67, 0.70, 0.73, 0.75, 0.82]
    thresh = bg.occupancy_threshold(scores)
    assert 0.30 < thresh <= 0.67
    assert 0.30 < thresh


def test_nms_removes_duplicate_boxes():
    dets = [
        {
            "bbox_x": 0.7,
            "bbox_y": 0.2,
            "bbox_w": 0.2,
            "bbox_h": 0.25,
            "confidence": 0.9,
            "source": "a",
        },
        {
            "bbox_x": 0.72,
            "bbox_y": 0.21,
            "bbox_w": 0.2,
            "bbox_h": 0.25,
            "confidence": 0.85,
            "source": "b",
        },
        {
            "bbox_x": 0.2,
            "bbox_y": 0.2,
            "bbox_w": 0.2,
            "bbox_h": 0.25,
            "confidence": 0.8,
            "source": "c",
        },
    ]
    out = bg.nms_detections(dets, iou_thresh=0.4)
    assert len(out) == 2
    confs = sorted((d["confidence"] for d in out), reverse=True)
    assert confs == [0.9, 0.8]


def test_reject_ring_margin_boxes():
    dets = [
        {
            "bbox_x": 0.85,
            "bbox_y": 0.4,
            "bbox_w": 0.14,
            "bbox_h": 0.2,
            "confidence": 0.7,
            "source": "ring",
        },
        {
            "bbox_x": 0.3,
            "bbox_y": 0.4,
            "bbox_w": 0.2,
            "bbox_h": 0.25,
            "confidence": 0.7,
            "source": "card",
        },
    ]
    out = bg.filter_page_margins(dets, min_cx=0.10, max_cx=0.88)
    assert len(out) == 1
    assert out[0]["source"] == "card"
