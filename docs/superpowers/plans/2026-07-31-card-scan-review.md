# Interactive Card Scan Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Photo-upload card scan with clickable overlays, Scryfall verification panel + list, and commit of name/set/collector#.

**Architecture:** Extend existing `vision/*` + collection scan API; enrich Scryfall metadata; persist `collector_number`; replace static overlay UX with positioned click targets and a detail panel. Build Scryfall-based fixture images for tests.

**Tech Stack:** Flask, SQLite, PIL, requests/Scryfall, pytest, vanilla JS

## Global Constraints

- Photo upload only (no live camera)
- Free detection (no fixed binder grid mode)
- Track name + set + collector_number + scryfall_id
- TDD: failing test before production code
- Do not commit secrets; Scryfall fixtures are public card art

---

### Task 1: Scryfall lookup returns image_uri + collector_number

**Files:**
- Modify: `src/magic_optimizer/vision/scryfall.py`
- Test: `tests/test_scryfall_lookup.py`

**Interfaces:**
- Produces: `lookup_card_name(name: str) -> dict | None` with keys `scryfall_id`, `card_name`, `set_code`, `collector_number`, `image_uri`

- [ ] **Step 1: Write failing test**

```python
from unittest.mock import patch, MagicMock
from magic_optimizer.vision.scryfall import lookup_card_name

def test_lookup_includes_image_uri_and_collector_number():
    payload = {
        "id": "abc",
        "name": "Lightning Bolt",
        "set": "m21",
        "collector_number": "162",
        "image_uris": {"small": "https://cards.scryfall.io/small/front/x.jpg"},
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = payload
    with patch("magic_optimizer.vision.scryfall.requests.get", return_value=mock_resp):
        # clear cache if module caches by name
        result = lookup_card_name("Lightning Bolt")
    assert result["collector_number"] == "162"
    assert result["image_uri"] == "https://cards.scryfall.io/small/front/x.jpg"
    assert result["set_code"] == "M21"
```

- [ ] **Step 2: Run test — expect FAIL** (missing `image_uri`)

Run: `pytest tests/test_scryfall_lookup.py::test_lookup_includes_image_uri_and_collector_number -v`

- [ ] **Step 3: Implement** — add `image_uri` from `image_uris.small` or first face `image_uris.small` for DFCs

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit** `feat(vision): return Scryfall image_uri in card lookup`

---

### Task 2: Persist and commit collector_number on scan detections

**Files:**
- Modify: `src/magic_optimizer/collection/db.py`
- Modify: `src/magic_optimizer/collection/repository.py`
- Modify: `tests/test_scan_session.py`

**Interfaces:**
- Produces: `create_scan_session` / `update_detection` / `commit_scan_session` handle `collector_number`

- [ ] **Step 1: Extend failing test** in `tests/test_scan_session.py`

```python
def test_commit_stores_collector_number(repo):
    user_id = repo.ensure_user("philipp")
    coll = repo.create_collection(user_id, "CN Test")
    session = repo.create_scan_session(
        coll["id"], user_id, "/tmp/scan.jpg",
        [{
            "bbox_x": 0.1, "bbox_y": 0.1, "bbox_w": 0.2, "bbox_h": 0.3,
            "detected_name": "Lightning Bolt",
            "set_code": "M21",
            "collector_number": "162",
            "scryfall_id": "abc",
            "status": "accepted",
        }],
    )
    assert session["detections"][0]["collector_number"] == "162"
    repo.commit_scan_session(session["id"], user_id)
    cards = repo.list_cards(coll["id"], user_id)
    assert cards[0]["collector_number"] == "162"
```

- [ ] **Step 2: Run — FAIL** (column / field missing)

- [ ] **Step 3: Schema + repository** — add column (CREATE + ALTER migrate), insert/update/commit fields

- [ ] **Step 4: PASS + commit** `feat(collection): persist collector_number on scan commit`

---

### Task 3: Overlay status colors (pending amber)

**Files:**
- Modify: `src/magic_optimizer/vision/overlay.py`
- Test: `tests/test_vision_overlay.py`

- [ ] **Step 1: Failing test** — pending → amber RGB, accepted green, rejected red

- [ ] **Step 2–4: Implement color map; PASS; commit** `feat(vision): amber pending overlay boxes`

---

### Task 4: Scryfall fixture image builder (single + 3×3)

**Files:**
- Create: `src/magic_optimizer/vision/fixtures.py`
- Create: `scripts/build_scan_fixtures.py`
- Test: `tests/test_scan_fixtures.py`
- Output: `tests/fixtures/scan/single.jpg`, `tests/fixtures/scan/binder_3x3.jpg`

**Interfaces:**
- Produces: `build_card_grid(card_image_paths: list[Path], cols: int, rows: int, out_path: Path, gap: int = 8) -> Path`
- Produces: `download_scryfall_normals(names: list[str], dest_dir: Path) -> list[Path]`

- [ ] **Step 1: Failing test** for `build_card_grid` using tiny synthetic PIL images (no network)

```python
def test_build_card_grid_3x3(tmp_path):
    from PIL import Image
    from magic_optimizer.vision.fixtures import build_card_grid
    cards = []
    for i in range(9):
        p = tmp_path / f"c{i}.jpg"
        Image.new("RGB", (100, 140), (i * 20, 40, 80)).save(p)
        cards.append(p)
    out = tmp_path / "grid.jpg"
    build_card_grid(cards, cols=3, rows=3, out_path=out, gap=4)
    img = Image.open(out)
    assert img.size == (100 * 3 + 4 * 4, 140 * 3 + 4 * 4)
```

- [ ] **Step 2–4: Implement grid composer; PASS**

- [ ] **Step 5: Script** downloads 9 real cards (rate-limit 100ms) into `tests/fixtures/scan/cards/` and writes `single.jpg` + `binder_3x3.jpg`; commit fixtures if size reasonable (< ~5MB) else generate in CI/test setup

- [ ] **Step 6: Commit** `feat(vision): Scryfall scan fixture builder`

---

### Task 5: API returns image_uri on detections

**Files:**
- Modify: `src/magic_optimizer/collection/routes.py`
- Modify: `src/magic_optimizer/vision/ocr.py` (pass collector_number through)
- Test: `tests/test_scan_api_enrichment.py`

- [ ] **Step 1: Failing Flask test** — after scan (mocked detect + lookup), JSON detection has `image_uri` and `collector_number`

- [ ] **Step 2–4: Enrich in route or helper `enrich_detection_response(det)`; PATCH updates collector_number; PASS; commit**

---

### Task 6: Interactive overlay UI + detail panel

**Files:**
- Modify: `templates/collections.html`
- Modify: `static/js/collections.js`
- Optional smoke: `tests/test_collections_scan_markup.py` asserts template contains `scanStage`, `scanDetailPanel`

- [ ] **Step 1: Markup** — `#scanStage` (relative) with `#scanOriginal` + `#scanBoxes`; `#scanDetailPanel` with img, name, set, Accept/Reject

- [ ] **Step 2: JS** — render boxes from bbox %; click opens panel; list Accept stays; sync status colors; use `original_url` not only overlay jpeg

- [ ] **Step 3: Manual check** with `binder_3x3.jpg` upload locally

- [ ] **Step 4: Commit** `feat(ui): clickable scan overlay and detail panel`

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Upload + free detect | existing + Task 4 fixtures |
| Clickable overlay + detail panel | Task 6 |
| Parallel accept list | Task 6 (keep existing list) |
| name/set/collector# | Tasks 1–2, 5 |
| Scryfall image preview | Tasks 1, 5–6 |
| Test images from Scryfall | Task 4 |
| No live camera | Global constraint |
