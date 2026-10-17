# Design: Three-Way Repository Split

**Date:** 2026-09-24  
**Status:** Approved for implementation  
**Project:** 03_Magic (MTG Sealed Deck Optimizer)

## 1. Goal

Split the monolithic `03_Magic` codebase into **three independent Git repositories** along clear domain boundaries, so Collection inventory work, Vision/card-ID work, and Deck Optimizer / sealed-AI work can evolve, deploy, and CI separately.

## 2. Context

Today one repo and one Flask host (`web_app.py`) mix:

- **Collection / inventory** — SQLite DB, Manabox/Moxfield imports, union export, trades, wishlist, scan sessions
- **Vision** — YOLO detect, binder grid, identify, OCR, Scryfall enrichment, training/models
- **Optimizer / sealed AI** — greedy/genetic/SA, deck_picker, league, match_oracle, dreamer, selfplay, sealed sim

`web_app.py` is not a fourth domain: it is a shared HTTP shell that registers blueprints from all of the above. It should be **split with the domains that need UI**, not moved into its own repo.

## 3. Decisions

| Topic | Choice |
|-------|--------|
| Split shape | **Three Git repos** (Ansatz 1) |
| Repo names (working) | `mtg-vision`, `mtg-collection`, `mtg-optimizer` |
| Flask shell | **Two small web apps** (Collection + Optimizer); Vision **headless** (CLI/Lib only) |
| Cross-repo contracts (MVP) | **File/JSON contracts** first; optional HTTP later |
| Shared host / 4th frontend repo | **Out of scope** |
| Monorepo alternative | Rejected for this effort |

## 4. Non-goals (MVP)

- Rewriting Optimizer or Collection business logic
- New React/SPA frontend or a dedicated frontend repo
- Live HTTP service mesh between all three (CSV/JSON is enough to start)
- Merging Vision into Collection as a single package
- Deleting `03_Magic` immediately (may remain archive / migration parent briefly)

## 5. Target repositories

### 5.1 `mtg-vision`

**Responsibility:** Image → structured card detections.

| In | Out |
|----|-----|
| `src/.../vision/` (detect, identify, binder_grid, ocr, overlay, yolo, scryfall helpers used only for ID) | Collection DB / ownership |
| `models/`, `weights/`, `training/` (card detect & ID) | Deck building, league, selfplay |
| CLI entrypoints / scripts: batch eval, overlays, id bakeoff | Flask UI |

**Public surface (MVP):** library + CLI that emit a card list, e.g.:

```json
{
  "detections": [
    {"name": "Lightning Bolt", "qty": 1, "set": "LEA", "collector_number": "161", "confidence": 0.92}
  ]
}
```

### 5.2 `mtg-collection`

**Responsibility:** Ownership — what the user owns, imports, trades, wishlist; orchestrates scans.

| In | Out |
|----|-----|
| `collection/` (db, repository, routes, auth, union_export) | Optimizer algorithms |
| `data/collections/` (or equivalent) | League / match_oracle / dreamer / selfplay |
| Small Flask app: inventar UI + scan upload → calls Vision | YOLO training |

**Depends on:** `mtg-vision` as library or CLI subprocess (pinned version).

**Public surface (MVP):** export of owned/pool cards (CSV compatible with today’s union export), plus existing collection HTTP APIs for its own UI.

### 5.3 `mtg-optimizer`

**Responsibility:** Pool → deck, evaluation, sealed training loops.

| In | Out |
|----|-----|
| optimizers, evaluators, deck_builder, deck_picker | Collection SQLite / inventar CRUD |
| league, match_oracle, dreamer, selfplay, meta/sealed_sim | Vision models / photo pipeline |
| pool_prune, synergy, exporters | Manabox import |
| Small Flask app: upload pool/CSV → optimize → download | |

**Depends on:** Collection only via **exported pool/owned CSV** (or later a thin HTTP read API). No direct DB access.

## 6. Architecture

```
Photo
  → mtg-vision (CLI/Lib)
  → detections JSON/CSV
  → mtg-collection (persist, review, inventar)
  → owned / union / pool CSV
  → mtg-optimizer (build deck, league, selfplay)
```

### Flask split

| Current | After split |
|---------|-------------|
| `web_app.py` routes `/`, `/upload`, `/optimize`, … | **mtg-optimizer** app |
| `collection_bp` (+ scan UI templates/JS) | **mtg-collection** app |
| Vision used only from collection routes/scripts | **mtg-vision** package; Collection imports or shells out |
| `deck_picker`, `league`, `match_oracle`, `dreamer`, `selfplay` blueprints | **mtg-optimizer** app |

### Contracts (MVP)

| From → To | Format | Notes |
|-----------|--------|-------|
| Vision → Collection | JSON list of detections | Stable field names; qty default 1 |
| Collection → Optimizer | CSV (name, qty, optional set/rating columns) | Prefer existing union-export shape |
| Optimizer → user | Deck export (Arena/MTGO/HTML) | Unchanged formats |

Version contracts in a short `CONTRACTS.md` in each consumer repo (and optionally a shared gist/doc in the archive repo during migration).

## 7. Migration plan (high level)

1. **Boundary pass in monorepo** — stop Collection→Optimizer and Optimizer→Vision imports; fix any reverse deps with contracts or thin adapters.
2. **Pin contract fixtures** — golden JSON/CSV samples + tests in each side.
3. **Extract `mtg-vision`** — move package + models/training + vision scripts; Collection depends on published/path install.
4. **Extract `mtg-collection`** — move collection + its Flask app + data; wire Vision dependency.
5. **Extract `mtg-optimizer`** — move optimizer stack + its Flask app; consume CSV only.
6. **Retire or archive `03_Magic`** — README points to the three repos; optional short-lived meta wrapper.

Order preference: Vision first (fewest inbound deps from Optimizer), then Collection, then Optimizer.

## 8. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports today (e.g. collection routes → vision; pool_prune → scryfall) | Move shared Scryfall HTTP helper into vision **or** a tiny shared util copied once; Optimizer must not import Vision long-term |
| Dual Flask apps drift | Keep each app thin; shared CSS/JS only if copied deliberately, not via fourth repo |
| Deploy/Docker today assumes one compose | One compose per repo; document ports |
| Large binary models in git | Keep models in `mtg-vision` (or object storage later); Collection/Optimizer do not duplicate weights |

## 9. Success criteria

- Three repos build and test independently
- Collection can run a scan using Vision without Optimizer installed
- Optimizer can build a deck from a Collection export CSV without Collection or Vision installed
- No single shared `web_app.py` hosting all domains

## 10. Open items (post-MVP)

- Optional Collection HTTP read API for live Optimizer UI
- Package publishing (private index / git tags) vs path deps
- Final public repo names and hosting (GitLab/GitHub)
- Whether `03_Magic` becomes a thin orchestrator README only or is deleted after cutover
