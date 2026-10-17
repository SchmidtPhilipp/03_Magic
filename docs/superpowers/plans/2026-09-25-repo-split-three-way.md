# Three-Way Repo Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare `03_Magic` for a clean three-repo split (`mtg-vision`, `mtg-collection`, `mtg-optimizer`) by locking contracts, removing cross-domain imports, splitting Flask into two apps (Vision headless), then extracting each repo in order.

**Architecture:** Keep work in this monorepo until boundaries are green. Vision owns image→detections; Collection owns inventar + scan orchestration and depends on Vision; Optimizer owns deck AI and consumes only Collection CSV exports. No fourth frontend repo; no shared `web_app.py` after cutover.

**Tech Stack:** Python 3.11+, Flask, pytest, existing `src/magic_optimizer` package, CSV/JSON file contracts, Docker Compose per repo (later).

**Spec:** `docs/superpowers/specs/2026-09-24-repo-split-three-way-design.md`

## Global Constraints

- Three Git repos eventually: **mtg-vision**, **mtg-collection**, **mtg-optimizer** (working names).
- Vision is **headless** (CLI/Lib only). Collection and Optimizer each get a **small Flask app**.
- MVP cross-repo I/O is **JSON/CSV files**, not a service mesh.
- Optimizer must **not** import Vision or Collection DB long-term.
- Collection may depend on Vision (library or CLI).
- No hardcoded SSH hosts; no secrets in code or commits.
- TDD where behavior changes: failing test → implement → pass → commit per task.
- Do **not** delete `03_Magic` in this plan; leave an archive README pointer after extract.
- Frequent commits; only when the executing user has asked for commits in that session (or the task explicitly requires one after user approval of the plan execution).

## File structure (target after Plan tasks in monorepo)

| Path | Responsibility |
|------|----------------|
| `contracts/vision_detections.schema.json` | Vision → Collection detection list schema |
| `contracts/fixtures/vision_detections_sample.json` | Golden Vision output |
| `contracts/fixtures/owned_pool_sample.csv` | Golden Collection → Optimizer CSV |
| `contracts/CONTRACTS.md` | Human-readable contract doc |
| `src/magic_optimizer/scryfall_client.py` | Shared Scryfall HTTP helper (no Vision/optimize coupling) |
| `src/magic_optimizer/vision/scryfall.py` | Thin re-export / wrapper around `scryfall_client` |
| `src/magic_optimizer/pool_prune/facts.py` | Uses `scryfall_client`, not `vision.scryfall` |
| `src/magic_optimizer/card_names.py` | `normalize_card_name`, `is_junk_match` (moved out of vision.identify for Collection CSV tools) |
| `apps/collection_app.py` | Flask host: `collection_bp` + inventar/scan templates |
| `apps/optimizer_app.py` | Flask host: optimize routes + deck_picker/league/… blueprints |
| `web_app.py` | Temporary shim that warns and can run one or both apps until cutover |

---

### Task 1: Contract fixtures and CONTRACTS.md

**Files:**
- Create: `contracts/CONTRACTS.md`
- Create: `contracts/vision_detections.schema.json`
- Create: `contracts/fixtures/vision_detections_sample.json`
- Create: `contracts/fixtures/owned_pool_sample.csv`
- Create: `tests/test_contracts_fixtures.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - Detection JSON shape: `{ "detections": [ { "name": str, "qty": int, "set": str|null, "collector_number": str|null, "confidence": float|null } ] }`
  - Owned CSV columns (minimum): `card_name`, `amount` (alias `name`/`qty` accepted later by adapter if needed)
  - Fixture files loadable by later tasks

- [ ] **Step 1: Write the failing test**

```python
# tests/test_contracts_fixtures.py
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "contracts" / "fixtures"


def test_vision_detections_fixture_shape():
    data = json.loads((FIX / "vision_detections_sample.json").read_text())
    assert "detections" in data
    assert len(data["detections"]) >= 1
    row = data["detections"][0]
    assert "name" in row and "qty" in row


def test_owned_pool_csv_has_required_columns():
    with (FIX / "owned_pool_sample.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        fields = {h.lower() for h in reader.fieldnames}
        assert "card_name" in fields or "name" in fields
        assert "amount" in fields or "qty" in fields
        rows = list(reader)
    assert len(rows) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_contracts_fixtures.py -v`  
Expected: FAIL (missing files / path)

- [ ] **Step 3: Write fixtures and CONTRACTS.md**

`contracts/fixtures/vision_detections_sample.json`:

```json
{
  "detections": [
    {
      "name": "Lightning Bolt",
      "qty": 1,
      "set": "LEA",
      "collector_number": "161",
      "confidence": 0.92
    }
  ]
}
```

`contracts/fixtures/owned_pool_sample.csv`:

```csv
card_name,amount,set_code
Lightning Bolt,4,LEA
Counterspell,2,ICE
```

`contracts/vision_detections.schema.json`: JSON Schema draft-07 object with required `detections` array and required properties `name`, `qty` on items.

`contracts/CONTRACTS.md`: Document Vision→Collection JSON and Collection→Optimizer CSV; note Optimizer has no DB access.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_contracts_fixtures.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (when user asks)

```bash
git add contracts tests/test_contracts_fixtures.py
git commit -m "$(cat <<'EOF'
docs: add vision/collection/optimizer split contracts

EOF
)"
```

---

### Task 2: Extract `scryfall_client` so Optimizer does not import Vision

**Files:**
- Create: `src/magic_optimizer/scryfall_client.py`
- Modify: `src/magic_optimizer/vision/scryfall.py` (delegate to client)
- Modify: `src/magic_optimizer/pool_prune/facts.py` (`_default_lookup` import)
- Test: `tests/test_scryfall_client_import_boundary.py`

**Interfaces:**
- Consumes: existing `vision.scryfall` behavior (`scryfall_get`, headers, timeout)
- Produces:
  - `scryfall_get(url: str, *, params: dict | None = None, timeout: float = 15) -> requests.Response`
  - `lookup_card_name(name: str) -> dict[str, Any] | None` (same return keys as today)
  - `pool_prune.facts` imports **only** `magic_optimizer.scryfall_client`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scryfall_client_import_boundary.py
import ast
from pathlib import Path

FACTS = Path("src/magic_optimizer/pool_prune/facts.py")


def test_facts_does_not_import_vision():
    tree = ast.parse(FACTS.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "vision" not in node.module, node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "vision" not in alias.name


def test_scryfall_client_exports_get():
    from magic_optimizer.scryfall_client import scryfall_get

    assert callable(scryfall_get)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scryfall_client_import_boundary.py -v`  
Expected: FAIL (`scryfall_client` missing and/or vision import still present)

- [ ] **Step 3: Implement client + rewire**

1. Move HTTP helpers from `vision/scryfall.py` into `scryfall_client.py` (same User-Agent, cache, `lookup_card_name`, `scryfall_get`, `attach_image_uri`).
2. Make `vision/scryfall.py` re-export from `scryfall_client` so Collection/Vision callers keep working.
3. In `pool_prune/facts.py`, change:

```python
from magic_optimizer.scryfall_client import scryfall_get
```

(remove `from magic_optimizer.vision.scryfall import scryfall_get`).

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_scryfall_client_import_boundary.py tests/test_pool_prune_dominance.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (when user asks)

```bash
git add src/magic_optimizer/scryfall_client.py src/magic_optimizer/vision/scryfall.py src/magic_optimizer/pool_prune/facts.py tests/test_scryfall_client_import_boundary.py
git commit -m "$(cat <<'EOF'
refactor: move Scryfall HTTP out of vision for optimizer boundary

EOF
)"
```

---

### Task 3: Move card-name helpers out of Vision for Collection CSV tools

**Files:**
- Create: `src/magic_optimizer/card_names.py`
- Modify: `src/magic_optimizer/vision/identify.py` (import from `card_names` or re-export)
- Modify: `src/magic_optimizer/collection/union_export.py`
- Test: `tests/test_card_names.py`
- Test: `tests/test_union_export_boundary.py`

**Interfaces:**
- Consumes: current `is_junk_match` / `normalize_card_name` logic in `vision/identify.py`
- Produces:
  - `normalize_card_name(name: str) -> str`
  - `is_junk_match(name: str) -> bool`
  - `union_export` imports these from `card_names`, and `lookup_card_name` from `scryfall_client` (not vision)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_card_names.py
from magic_optimizer.card_names import is_junk_match, normalize_card_name


def test_normalize_strips_and_lower_key_stable():
    assert normalize_card_name("  Lightning Bolt ") == normalize_card_name("Lightning Bolt")


def test_junk_match_rejects_unknown_tokens():
    # Use a known junk pattern already used in identify.py today
    assert is_junk_match("unbekannt") or not is_junk_match("Lightning Bolt")
```

```python
# tests/test_union_export_boundary.py
import ast
from pathlib import Path

UNION = Path("src/magic_optimizer/collection/union_export.py")


def test_union_export_does_not_import_vision():
    tree = ast.parse(UNION.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "vision" not in node.module, f"unexpected: {node.module}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_card_names.py tests/test_union_export_boundary.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

1. Copy `normalize_card_name` and `is_junk_match` implementations into `card_names.py`.
2. Update `identify.py` to import from `card_names` (keep re-exports if other scripts import from identify).
3. Update `union_export.py`:

```python
from magic_optimizer.card_names import is_junk_match, normalize_card_name
from magic_optimizer.scryfall_client import lookup_card_name
```

- [ ] **Step 4: Run related tests**

Run: `pytest tests/test_card_names.py tests/test_union_export_boundary.py tests/test_union_export.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (when user asks)

```bash
git add src/magic_optimizer/card_names.py src/magic_optimizer/vision/identify.py src/magic_optimizer/collection/union_export.py tests/test_card_names.py tests/test_union_export_boundary.py
git commit -m "$(cat <<'EOF'
refactor: extract card_names so collection CSV tools avoid vision

EOF
)"
```

---

### Task 4: Dual Flask apps in monorepo (Collection vs Optimizer)

**Files:**
- Create: `apps/collection_app.py`
- Create: `apps/optimizer_app.py`
- Modify: `web_app.py` (optional thin launcher / deprecation note at top)
- Create: `tests/test_dual_apps_blueprints.py`
- Keep: `templates/collections.html`, `static/js/collections.js` with Collection app
- Keep: `templates/index.html`, `static/js/app.js` with Optimizer app

**Interfaces:**
- Consumes: existing blueprints (`collection_bp`, `deck_picker_bp`, `league_bp`, `match_oracle_bp`, `dreamer_bp`, `selfplay_bp`) and optimize routes currently in `web_app.py`
- Produces:
  - `create_collection_app() -> Flask` registering only `collection_bp` (+ static/templates)
  - `create_optimizer_app() -> Flask` registering optimize routes + optimizer blueprints, **not** `collection_bp`
  - Collection app may still `import magic_optimizer.vision` for scan (allowed)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dual_apps_blueprints.py
def test_collection_app_has_collection_not_league():
    from apps.collection_app import create_collection_app

    app = create_collection_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    # collection routes exist under /collections or similar — assert blueprint name registered
    assert "collection" in {bp.name for bp in app.blueprints.values()} or any(
        "collection" in r for r in rules
    )
    assert "league" not in app.blueprints


def test_optimizer_app_has_no_collection_blueprint():
    from apps.optimizer_app import create_optimizer_app

    app = create_optimizer_app()
    assert "collection" not in app.blueprints
    assert "deck_picker" in app.blueprints or any(
        "deck" in r.rule for r in app.url_map.iter_rules()
    )
```

Adjust assertions to match actual blueprint `.name` values from `collection/routes.py` and `deck_picker/api.py` after reading those files.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dual_apps_blueprints.py -v`  
Expected: FAIL (modules missing)

- [ ] **Step 3: Implement dual apps**

1. Factor route handlers from `web_app.py` that are optimizer-only into functions importable by `apps/optimizer_app.py` **or** move the optimize routes into a new `magic_optimizer.optimizer_web.routes` blueprint if cleaner — prefer minimal move: copy/register the same routes in `create_optimizer_app`.
2. `create_collection_app`: `init_db()`, register `collection_bp` only.
3. `create_optimizer_app`: register deck_picker, match_oracle, league, dreamer, selfplay + optimize UI routes; do **not** register `collection_bp`.
4. Leave `web_app.py` as a temporary combined entry for one release, with a log line: `"DEPRECATED: use apps.collection_app or apps.optimizer_app"`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_dual_apps_blueprints.py tests/test_collection_repository.py tests/test_deck_picker_api.py -v`  
Expected: PASS

- [ ] **Step 5: Manual smoke (optional but recommended)**

```bash
# terminal 1
python -c "from apps.collection_app import create_collection_app; create_collection_app().run(port=5001)"
# terminal 2
python -c "from apps.optimizer_app import create_optimizer_app; create_optimizer_app().run(port=5002)"
```

Expected: Collection UI on :5001, Optimizer UI on :5002 without sharing one process.

- [ ] **Step 6: Commit** (when user asks)

```bash
git add apps web_app.py tests/test_dual_apps_blueprints.py
git commit -m "$(cat <<'EOF'
feat: split Flask into collection and optimizer apps

EOF
)"
```

---

### Task 5: Boundary guard — Optimizer package tree must not import Vision/Collection

**Files:**
- Create: `tests/test_domain_import_boundaries.py`

**Interfaces:**
- Consumes: package layout under `src/magic_optimizer/`
- Produces: AST-based CI guard that fails if optimizer modules import vision or collection

Optimizer roots (scan these directories recursively):  
`optimizers/`, `evaluators/`, `deck_picker/`, `league/`, `match_oracle/`, `dreamer/`, `selfplay/`, `meta/`, `pool_prune/`, `synergy/`, `exporters/`, plus `deck_builder.py`, `optimizer.py`, `evaluator.py`.

Allowed: `scryfall_client`, `card_names`, stdlib, third-party.

- [ ] **Step 1: Write the failing test (or passing if Task 2–3 done)**

```python
# tests/test_domain_import_boundaries.py
import ast
from pathlib import Path

ROOT = Path("src/magic_optimizer")
OPTIMIZER_DIRS = [
    "optimizers", "evaluators", "deck_picker", "league", "match_oracle",
    "dreamer", "selfplay", "meta", "pool_prune", "synergy", "exporters",
]
OPTIMIZER_FILES = ["deck_builder.py", "optimizer.py", "evaluator.py"]
FORBIDDEN = ("magic_optimizer.vision", "magic_optimizer.collection")


def _modules_in(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_optimizer_tree_avoids_vision_and_collection():
    paths: list[Path] = []
    for d in OPTIMIZER_DIRS:
        paths.extend((ROOT / d).rglob("*.py"))
    for f in OPTIMIZER_FILES:
        paths.append(ROOT / f)
    bad = []
    for path in paths:
        if not path.is_file():
            continue
        for mod in _modules_in(path):
            if any(mod == f or mod.startswith(f + ".") for f in FORBIDDEN):
                bad.append(f"{path}: {mod}")
    assert bad == [], "\n".join(bad)
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_domain_import_boundaries.py -v`  
Expected: PASS after Tasks 2–3; if FAIL, fix remaining imports before extract

- [ ] **Step 3: Commit** (when user asks)

```bash
git add tests/test_domain_import_boundaries.py
git commit -m "$(cat <<'EOF'
test: guard optimizer packages against vision/collection imports

EOF
)"
```

---

### Task 6: Extract checklist — `mtg-vision` (new Git repo)

**Files (move into new repo):**
- `src/magic_optimizer/vision/` → package rename optional (`mtg_vision` or keep path)
- `models/`, `weights/`, `training/` (card detect/ID)
- Vision scripts: `scripts/batch_eval_scans.py`, `scripts/detection_scorecard.py`, `scripts/id_*.py`, `scripts/render_s3_overlays.py`, `scripts/build_scan_fixtures.py`
- Related tests: `tests/test_yolo_detect.py`, `tests/test_binder_grid*.py`, `tests/test_identify_s3.py`, `tests/test_scan_*.py`, fixtures under `tests/fixtures/scan/`
- `contracts/vision_detections.schema.json` + sample fixture (copy)
- Depends on: `scryfall_client.py` **or** vendor a copy inside vision package

**Steps:**

- [ ] **Step 1:** Create empty repo `mtg-vision` (GitLab/GitHub as preferred by user).
- [ ] **Step 2:** Copy files listed above; add minimal `pyproject.toml` / `requirements-vision.txt`; README with CLI: image path → JSON detections matching contract.
- [ ] **Step 3:** Add CLI entrypoint e.g. `python -m mtg_vision.cli path/to.jpg -o detections.json`.
- [ ] **Step 4:** Run vision tests in the new repo until green.
- [ ] **Step 5:** In `03_Magic`, document path/git dependency: Collection installs Vision from tag or path.
- [ ] **Step 6:** Commit in both repos when user asks.

**Done when:** Vision repo tests pass; Collection can still scan via path-install of Vision.

---

### Task 7: Extract checklist — `mtg-collection`

**Files (move into new repo):**
- `src/magic_optimizer/collection/`
- `apps/collection_app.py`
- `templates/collections.html`, `static/js/collections.js` (+ shared CSS as needed)
- `data/collections/` (or document external data dir)
- `card_names.py`, `scryfall_client.py` (or depend on vision for Scryfall only — prefer keep `scryfall_client` + `card_names` here too if Vision is optional for CSV-only use)
- Scripts: `scripts/export_collection_union.py`, `scripts/match_friend_trades.py`, `scripts/build_deck_collection.py` (if inventar-focused)
- Tests: `tests/test_collection_*.py`, `tests/test_union_export*.py`, `tests/test_trade_report.py`
- Contract: owned CSV fixture + `CONTRACTS.md` section

**Steps:**

- [ ] **Step 1:** Create `mtg-collection` repo; copy files; depend on `mtg-vision` for detect/overlay.
- [ ] **Step 2:** Wire `create_collection_app` as main entry (`start_app.sh` equivalent).
- [ ] **Step 3:** Ensure scan path: upload → Vision lib/CLI → detections JSON → repository.
- [ ] **Step 4:** Export CLI writes CSV matching `owned_pool_sample.csv` columns.
- [ ] **Step 5:** Run collection tests green; smoke Flask on a free port.
- [ ] **Step 6:** Commit when user asks.

**Done when:** Collection runs inventar + scan without Optimizer installed.

---

### Task 8: Extract checklist — `mtg-optimizer`

**Files (move into new repo):**
- Optimizer package dirs listed in Task 5 + `card.py`, `validator.py`, `deck_builder.py`, etc.
- `apps/optimizer_app.py`
- `templates/index.html`, `deck_export_artwork.html`, `land_sac_gallery.html`, `static/js/app.js`
- Scripts: `scripts/run_selfplay_loop.py`, `scripts/run_sealed_train_continuous.py`, `scripts/simulate_sealed_pool.py`, `scripts/allocate_multi_decks.py`, `scripts/prune_and_synergy_report.py`, `scripts/export_verified_decks.py`, `scripts/render_deck_find_html.py`, …
- Tests for those modules; `contracts/fixtures/owned_pool_sample.csv`
- `data/ratings/`, `data/decks/` as needed
- **Exclude:** `collection/`, `vision/`, `data/collections/` inventar DB

**Steps:**

- [ ] **Step 1:** Create `mtg-optimizer` repo; copy files; **no** dependency on Collection/Vision packages.
- [ ] **Step 2:** Optimize UI loads pool via upload of owned CSV (fixture must work end-to-end).
- [ ] **Step 3:** Run optimizer/deck_picker/league/selfplay tests green.
- [ ] **Step 4:** Smoke: `create_optimizer_app` + upload `owned_pool_sample.csv` → deck download.
- [ ] **Step 5:** Commit when user asks.

**Done when:** Optimizer builds a deck from Collection export CSV with neither Collection nor Vision installed.

---

### Task 9: Archive pointer in `03_Magic`

**Files:**
- Modify: `README.md` (top section: split status + links)
- Create: `SPLIT.md` optional short status

- [ ] **Step 1:** Add README section listing the three repos, ports, and which app to run.
- [ ] **Step 2:** Note `web_app.py` deprecated in favor of per-repo apps.
- [ ] **Step 3:** Commit when user asks.

**Done when:** A new contributor opening `03_Magic` knows where active development lives.

---

## Spec coverage (self-review)

| Spec item | Task(s) |
|-----------|---------|
| Three repos Vision / Collection / Optimizer | 6, 7, 8 |
| Two Flask apps; Vision headless | 4, 6 |
| File/JSON contracts MVP | 1 |
| Optimizer no Collection DB / no Vision | 2, 3, 5, 8 |
| Collection depends on Vision | 6, 7 |
| Migration order Vision → Collection → Optimizer | 6 → 7 → 8 |
| Do not delete 03_Magic immediately | 9 |
| No 4th frontend repo | 4 (explicit non-goal) |

## Execution note

Tasks **1–5** are executable inside this monorepo now. Tasks **6–8** need remote/empty repos and user choice of hosting; treat each extract as its own agent session after 1–5 are green.
