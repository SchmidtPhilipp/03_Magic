# Proxy print pipeline

Normalize alternate-art card images to the Scryfall cache size (**488×680**) and export **A4** PDF sheets with cards at real physical size (**63.5 × 88.9 mm**). Default layout is **3×3 = 9 cards per page** (margins tuned in `data/proxy/config.yaml`).

**Design spec:** [`docs/superpowers/specs/2026-10-23-proxy-print-pipeline-design.md`](../superpowers/specs/2026-10-23-proxy-print-pipeline-design.md)

## Layout

```
data/proxy/
  config.yaml          # reference pixels, card mm, A4 margins/gap
  manifest.yaml        # arts registry
  originals/PHI/       # imported sources (never overwrite without --force)
  normalized/PHI/      # exact 488×680
  prints/              # generated PDFs
```

## PHI batch (12 arts)

| art_id | Card | oracle_set |
|--------|------|------------|
| `volcanic-island__phi-0001` | Volcanic Island | 3ED |
| `badlands__phi-0002` | Badlands | 3ED |
| `bayou__phi-0003` | Bayou | 3ED |
| `tropical-island__phi-0004` | Tropical Island | 3ED |
| `tundra__phi-0005` | Tundra | 3ED |
| `underground-sea__phi-0006` | Underground Sea | 3ED |
| `savannah__phi-0007` | Savannah | 3ED |
| `scrubland__phi-0008` | Scrubland | 3ED |
| `plateau__phi-0009` | Plateau | 3ED |
| `taiga__phi-0010` | Taiga | 3ED |
| `lotus-petal__phi-0011` | Lotus Petal | TMP |
| `city-of-traitors__phi-0012` | City of Traitors | EXO |

Smoke sheet qty list: `data/proxy/prints/phi-smoke-qty.txt` → PDF `data/proxy/prints/phi-smoke-sheet.pdf`.

## Commands

From the repo root (`03_Magic`), with `PYTHONPATH=src` (or `~/miniforge3/bin/python`):

```bash
# Import (copy into originals/, append manifest)
PYTHONPATH=src python scripts/proxy_import.py \
  --source /path/to/art.jpg \
  --card-name "Volcanic Island" \
  --art-id phi-0001 \
  --edition PHI

# Normalize all (or --art-id volcanic-island__phi-0001)
PYTHONPATH=src python scripts/proxy_normalize.py --all

# Validate (exit 0 when clean)
PYTHONPATH=src python scripts/proxy_validate.py

# Print PDF from a qty list
PYTHONPATH=src python scripts/proxy_print.py \
  --list data/proxy/prints/phi-smoke-qty.txt \
  --out data/proxy/prints/phi-smoke-sheet.pdf
```

### Qty list format

```
# comments and blank lines ok
4 Volcanic Island
1 volcanic-island__phi-0001
```

Each line is `N` + card name **or** `art_id`. Names prefer the configured edition (default `PHI`) and a normalized image when present.

## Printer settings

- Paper: **A4**
- Scale: **100% / actual size** — never fit-to-page
- Do **not** use “fit”, “shrink to printable area”, or borderless scaling that resizes content

Cards are drawn at fixed millimetres on the page. Fitting the PDF to the printer’s printable area will shrink the proxies and they will not match sleeve size.

Default grid (A4 portrait, margins L/R 5 mm + T/B 8 mm, **gap 0 mm**, **centered**) is **3×3** (9 cards/page). Cards get **rounded corners** (`corner_radius_mm: 2.5`). Wider margins drop to 2×3. Landscape fits more columns. Overflow continues on the next page.

### Duplex (backs)

- Front: `prints/phi-play-sheet.pdf`
- Backs (columns mirrored for long-edge flip): `prints/phi-play-backs.pdf`
- Combined: `prints/phi-play-duplex.pdf`

Print duplex with **long-edge binding** / flip on long edge, **100% / actual size**. Card back art: `originals/PHI/card-back__phi-back.jpg` (PHI-branded, not the official WotC back).
