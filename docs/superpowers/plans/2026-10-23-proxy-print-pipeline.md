# Proxy Print Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a proxy print pipeline to `03_Magic` with PHI alternate arts, 488×680 normalization, and A4 PDF sheets at real card size.

**Architecture:** Library under `src/magic_optimizer/proxy/` + CLI scripts; data under `data/proxy/`; Volcanic Island imported first; remaining PHI arts generated/imported as framed proxies.

**Tech Stack:** Python 3, Pillow, pytest; reportlab (or Pillow+PDF) for A4 PDFs; PyYAML for config/manifest.

## Global Constraints

- Repo root: `/Users/PhilippSchmidt/Documents/cursor/03_Magic`
- Pixel reference: exactly **488 × 680**; physical card **63.5 × 88.9 mm**
- Never overwrite files in `data/proxy/originals/` without explicit force
- Do not `git push` / Keychain git remotes; commit only if user asked (default: no commit unless task says so)
- Prefer extending existing patterns; keep modules small and testable
- User-provided Volcanic Island (preferred):  
  `/Users/PhilippSchmidt/.cursor/projects/Users-PhilippSchmidt-Documents-cursor/assets/Vulkaninsel_im_tropischen_Sonnenuntergang-30f7ca90-c6a6-44b8-b7a3-410e4c1703df.jpg`

---

## Task 1: Scaffold config, manifest, normalize, validate + tests

**Files:**
- Create `data/proxy/config.yaml`
- Create `data/proxy/manifest.yaml` (empty arts list or stub)
- Create `src/magic_optimizer/proxy/{__init__,config,manifest,normalize,validate}.py`
- Create `tests/proxy/test_normalize.py`, `tests/proxy/test_manifest.py`
- Update `requirements.txt` with `PyYAML` if missing; keep Pillow

- [x] Write failing tests for cover-crop → 488×680 and duplicate art_id rejection
- [x] Implement config load (paths relative to `data/proxy/`)
- [x] Implement normalize (Pillow LANCZOS, center crop)
- [x] Implement manifest load/validate
- [x] Run `PYTHONPATH=src pytest tests/proxy/ -q` — pass

---

## Task 2: Layout + PDF + print/validate scripts + tests

**Files:**
- Create `src/magic_optimizer/proxy/{layout,pdf}.py`
- Create `scripts/proxy_{import,normalize,print,validate}.py`
- Create `tests/proxy/test_layout.py`, `tests/proxy/test_pdf.py`
- Add `reportlab` to requirements if used
- Create `docs/proxy/README.md` (usage + print at 100%)

- [x] Layout computes cols/rows from A4 + margins + card mm + gap
- [x] PDF places images at exact mm; A4 page size
- [x] Scripts wire import (copy-only), normalize, print from qty list, validate
- [x] Tests pass

---

## Task 3: Import Volcanic Island + PHI manifest seed

**Files:**
- Copy user art → `data/proxy/originals/PHI/volcanic-island__phi-0001.jpg`
- Update `manifest.yaml` with Volcanic Island entry
- Run normalize → `normalized/PHI/...`
- Optional smoke PDF with 1–9 copies

- [x] Import without mutating source asset
- [x] Normalize to 488×680
- [x] Validate CLI exits 0

---

## Task 4: Generate remaining PHI full-art proxies (11 cards)

Cards 0002–0012: Badlands, Bayou, Tropical Island, Tundra, Underground Sea, Savannah, Scrubland, Plateau, Taiga, Lotus Petal, City of Traitors.

Style match Volcanic Island reference (full art, PHI footer, black border). Prefer programmatic frame composite over inconsistent random gens if needed; store under `originals/PHI/`, register in manifest, normalize.

- [x] All 11 present in originals + manifest
- [x] All normalized 488×680
- [x] `proxy_validate` clean

---

## Task 5: Integration smoke + docs polish

- [x] Print sheet PDF for PHI set (at least one page)
- [x] README covers import → normalize → print → printer settings
- [x] Spec path linked from README
