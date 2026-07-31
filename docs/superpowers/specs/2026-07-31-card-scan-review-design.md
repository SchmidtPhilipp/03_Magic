# Design: Interactive Card Scan Review

**Date:** 2026-07-31  
**Status:** Approved for implementation  
**Project:** 03_Magic (MTG Sealed Deck Optimizer)

## 1. Goal

Make collection intake via photo upload effective: detect cards freely in a photo (1–9+), show clickable overlays, verify each match against Scryfall (name + set + collector number), and commit accepted cards into the collection.

## 2. Context

Existing stack already covers upload → YOLO/OpenCV detect → OCR → Scryfall fuzzy name → `scan_sessions` / `scan_detections` → accept/reject list → commit. The UI is list-only; the overlay is a static JPEG without click targets. `collector_number` is looked up but not persisted on detections or commit.

## 3. Decisions

| Topic | Choice |
|-------|--------|
| Capture | Photo upload only (live camera later) |
| Detection | Free detection (no fixed 3×3 binder grid) |
| Verification | Click overlay box → detail panel **and** parallel accept list |
| Tracked fields | `card_name`, `set_code`, `collector_number`, `scryfall_id` |
| Approach | Enhance existing scan pipeline + Collections UI (no new workflow) |

## 4. Non-goals (MVP)

- Live webcam stream
- Fixed binder-slot grid enforcement
- Condition / foil tracking
- Image-hash / artwork similarity matching (OCR + Scryfall name remains primary)

## 5. Architecture

```
Upload (multipart)
  → detect_card_regions (YOLO → OpenCV → OCR enrichment)
  → Scryfall lookup enriches name, set, collector#, scryfall_id, image_uri
  → persist scan_session + scan_detections
  → JSON: detections + original_url (+ optional overlay_url)

UI
  → show original image with absolute-positioned clickable boxes (bbox %)
  → click box → detail panel (Scryfall art, editable name/set, Accept/Reject)
  → parallel detection list with Accept/Reject (same PATCH API)
  → Commit accepted → collection_cards (unique key bumps amount)
```

### Components

| Unit | Responsibility |
|------|----------------|
| `vision/scryfall.py` | Fuzzy lookup; return id, name, set, collector#, small image URI |
| `vision/detect.py` + `ocr.py` | Unchanged detection order; pass through Scryfall fields |
| `collection/db.py` | `scan_detections.collector_number` column |
| `collection/repository.py` | Persist/update/commit `collector_number` |
| `collection/routes.py` | Scan API returns `image_uri` on detections; PATCH may refresh Scryfall meta |
| `templates/collections.html` + `static/js/collections.js` | Clickable overlay, detail panel, list |

### Test fixtures

Script/module builds synthetic binder/table photos from Scryfall card images (single + 3×3 grid) under `tests/fixtures/scan/` for detector and UI-smoke tests without real camera photos.

## 6. Data model changes

Add to `scan_detections`:

- `collector_number TEXT` (nullable)

`commit_scan_session` must pass `collector_number` into `add_card`.

## 7. API contract (extensions)

Unchanged routes; richer detection objects:

```json
{
  "id": 1,
  "bbox_x": 0.1, "bbox_y": 0.1, "bbox_w": 0.2, "bbox_h": 0.3,
  "detected_name": "Lightning Bolt",
  "set_code": "M21",
  "collector_number": "162",
  "scryfall_id": "…",
  "image_uri": "https://cards.scryfall.io/small/…",
  "confidence": 0.7,
  "status": "pending"
}
```

`image_uri` may be filled at response time from cache/lookup if not stored (DB need not persist URI).

PATCH `/api/scan/<id>/detections/<det_id>`:

- On `detected_name` change → re-lookup Scryfall; update name, set, collector#, scryfall_id
- On `status` → `accepted` | `rejected` | `pending`

## 8. UI behavior

1. After upload: interactive stage (original image + boxes). Box colors: pending yellow/amber, accepted green, rejected red.
2. Click box or list row: open detail panel with Scryfall image (or placeholder), name/set inputs, Accept / Reject.
3. List always visible with Accept / Reject and inline name edit.
4. Commit button adds only `accepted` detections with a real name (not empty / `Unbekannt`).

## 9. Error handling

- No detections → empty panel + user message (existing alert).
- Scryfall miss → keep OCR/raw name; `image_uri` null; user edits name to trigger re-lookup.
- Network failure on lookup → leave fields unchanged; do not fail the whole scan.

## 10. Testing

- Unit: Scryfall lookup fields; repository commit with collector_number; overlay colors by status.
- Fixture builder: download N cards, compose single + 3×3 JPEG; assert file exists and grid geometry.
- API: scan response includes enriched fields (fixture image + mocked Scryfall where needed).
- No live camera tests.

## 11. Success criteria

- Upload of a multi-card fixture yields ≥1 clickable detection region in the UI data model.
- Accepting a detection and committing stores name + set + collector_number in `collection_cards`.
- Wrong name can be corrected in the detail panel and re-resolved via Scryfall before commit.
