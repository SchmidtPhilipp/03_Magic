"""API enrichment for scan detections (image_uri)."""

from unittest.mock import patch

from magic_optimizer.vision.scryfall import attach_image_uri


def test_attach_image_uri_uses_lookup():
    det = {"detected_name": "Lightning Bolt", "set_code": "M21"}
    with patch(
        "magic_optimizer.vision.scryfall.lookup_card_name",
        return_value={
            "card_name": "Lightning Bolt",
            "set_code": "M21",
            "collector_number": "162",
            "scryfall_id": "abc",
            "image_uri": "https://example.com/bolt.jpg",
        },
    ):
        out = attach_image_uri(det)
    assert out["image_uri"] == "https://example.com/bolt.jpg"
    assert out["collector_number"] == "162"


def test_attach_image_uri_keeps_existing():
    det = {
        "detected_name": "X",
        "image_uri": "https://example.com/x.jpg",
        "collector_number": "1",
    }
    out = attach_image_uri(det)
    assert out["image_uri"] == "https://example.com/x.jpg"
