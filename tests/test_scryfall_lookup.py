"""Tests for Scryfall scan lookup enrichment."""

from unittest.mock import MagicMock, patch

import magic_optimizer.vision.scryfall as scryfall


def test_lookup_includes_image_uri_and_collector_number():
    scryfall._CACHE.clear()
    payload = {
        "id": "abc-123",
        "name": "Lightning Bolt",
        "set": "m21",
        "collector_number": "162",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/x.jpg",
        },
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = payload
    with patch.object(scryfall.requests, "get", return_value=mock_resp) as mock_get:
        result = scryfall.lookup_card_name("Lightning Bolt")
        assert "User-Agent" in mock_get.call_args.kwargs.get("headers", {})

    assert result is not None
    assert result["collector_number"] == "162"
    assert result["set_code"] == "M21"
    assert result["card_name"] == "Lightning Bolt"
    assert result["scryfall_id"] == "abc-123"
    assert result["image_uri"] == "https://cards.scryfall.io/small/front/x.jpg"


def test_lookup_dfc_uses_first_face_image():
    scryfall._CACHE.clear()
    payload = {
        "id": "dfc-1",
        "name": "Delver of Secrets // Insectile Aberration",
        "set": "isd",
        "collector_number": "51",
        "card_faces": [
            {
                "image_uris": {
                    "small": "https://cards.scryfall.io/small/front/d.jpg",
                }
            }
        ],
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = payload
    with patch.object(scryfall.requests, "get", return_value=mock_resp):
        result = scryfall.lookup_card_name("Delver of Secrets")

    assert result["image_uri"] == "https://cards.scryfall.io/small/front/d.jpg"
