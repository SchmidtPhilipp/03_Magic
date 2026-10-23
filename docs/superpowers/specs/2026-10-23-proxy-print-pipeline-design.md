# Design: Magic Proxy Print Pipeline & PHI Alternate Arts

**Date:** 2026-10-23  
**Status:** Approved  
**Project:** `03_Magic`  
**Approach:** Module inside existing repo (`src/magic_optimizer/proxy/`)

## 1. Goal

Manage alternate-art card images, normalize them to the Scryfall cache reference size, and export print-ready A4 PDFs with correct physical card dimensions. Seed PHI edition with Volcanic Island (provided) plus generated full-art proxies for remaining duals, Lotus Petal, and City of Traitors.

## 2. Context (measured)

| Item | Value |
|------|--------|
| Repo | `03_Magic` |
| Scryfall cache | `static/card_cache/*.jpg` |
| Pixel reference | **488 × 680** (aspect ≈ 0.7176) |
| Physical card | **63.5 × 88.9 mm** |
| Stack | Python, Pillow (existing), pytest; add `reportlab` only if needed for PDF |
| Existing PHI arts | Volcanic Island only (user-provided); others generated |

## 3. Directory layout

```
data/proxy/
  config.yaml
  manifest.yaml
  originals/PHI/          # never overwrite in place
  normalized/PHI/         # exact 488×680 outputs
  prints/                 # generated PDFs (gitignored optional)
src/magic_optimizer/proxy/
  config.py, manifest.py, normalize.py, layout.py, pdf.py, validate.py
scripts/
  proxy_import.py, proxy_normalize.py, proxy_print.py, proxy_validate.py
tests/proxy/
docs/proxy/README.md
```

**Filename:** `{scryfall-slug}__{edition}-{nnnn}.{ext}`  
Example: `volcanic-island__phi-0001.jpg`

## 4. Manifest

YAML list of arts. Fields (only when known):

- `card_name`, optional `scryfall_id`, optional `oracle_set` (e.g. `3ED`)
- `edition` (`PHI`), `art_id`, `collector_number`
- `source_path`, `normalized_path`
- `pixel_width` / `pixel_height` (after normalize)
- `imported_at`, `status` ∈ `imported` | `normalized` | `print_ready` | `rejected`
- Multiple arts per card = multiple entries

## 5. Image pipeline

1. Import → copy into `originals/` (refuse overwrite unless `--force`)
2. Normalize: center cover-crop to reference aspect → resize to **exactly** 488×680 (no stretch)
3. Never mutate originals
4. Validate: missing files, bad format, wrong pixels, aspect tolerance, duplicate `art_id`, missing identifiers

## 6. A4 PDF layout

- Input: deck/qty list + preferred `art_id` / edition (PHI) / Scryfall cache fallback
- Page: A4 portrait (default) or landscape
- Card slot: always 63.5 × 88.9 mm (no fit-to-page scaling of cards)
- Configurable margins, gaps, optional crop marks
- Max grid from printable area; overflow → new page (typical 3×3 = 9)
- Print instruction: **100% / actual size**, not “fit to page”

## 7. PHI batch (full framed proxies)

| # | Card |
|---|------|
| 0001 | Volcanic Island (user art) |
| 0002–0010 | Badlands, Bayou, Tropical Island, Tundra, Underground Sea, Savannah, Scrubland, Plateau, Taiga |
| 0011 | Lotus Petal |
| 0012 | City of Traitors |

Style: borderless full-art, dual-color name/type bars where applicable, `PHI • EN`, artist line, black print border — match Volcanic Island reference.

Art generation is an import source; the print pipeline treats generated files like any other original.

## 8. Tests

- Geometry: crop + 488×680
- Manifest validation errors
- Layout: grid math, mm placement, multi-page qty
- PDF page size A4; cards not outside printable area

## 9. Non-goals (MVP)

Web UI, automatic OCR of frames, selling/distribution, merging into magic-viz.
