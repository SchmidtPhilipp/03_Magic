# Polish: Trade Report, Exports, Job Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add trade-oriented missing-card reports, name-list deck exports (Arena/copy-paste), and observe-only job progress / Forge health for league jobs.

**Architecture:** Thin helpers under `deck_picker` (trade report), `exporters` (name-list text), and `league` (progress snapshot + API). No new infra; CI-safe.

**Tech Stack:** Python 3.11+, pytest, Flask.

## Global Constraints

- TDD per task; `PYTHONPATH=src`; commit after each task.
- No SSH; Forge health is observe-only (`forge_available`).
- Basics excluded from trade/missing reports (existing rule).

## File structure

| Path | Responsibility |
|------|----------------|
| `src/magic_optimizer/deck_picker/trade.py` | Trade report from deck vs owned |
| `src/magic_optimizer/exporters/name_list.py` | Arena / copy-paste from `list[str]` |
| `src/magic_optimizer/league/progress.py` | Job progress snapshot |
| `src/magic_optimizer/league/api.py` | `/progress`, `/export`, `/trade-report` |
| `tests/test_trade_report.py` | TDD |
| `tests/test_name_list_export.py` | TDD |
| `tests/test_league_progress.py` | TDD |
| `tests/test_league_polish_api.py` | TDD |

---

### Task 1: Trade report

**Files:** Create `trade.py`; Test `tests/test_trade_report.py`

**Interfaces:**
- `def trade_report(deck: list[CardRef] | list[str], owned: CardPool) -> dict`
  - `missing: list[tuple[str,int]]` (reuse `missing_cards`)
  - `surplus: list[tuple[str,int]]` — owned copies beyond deck need for non-basics that appear in owned (optional: only cards in deck with owned > need → 0 surplus for those; surplus = owned qty for cards not in deck? Spec: trade planning → surplus = owned - needed for cards in deck where owned > needed, plus note total missing count)
  - Simpler MVP: `{missing, owned_covered: list[tuple[str,int]], missing_total, unique_missing}` where `owned_covered` is min(needed, owned) per deck card

Actually keep clear:
```python
{
  "missing": [["Shock", 2], ...],
  "present": [["Bolt", 4], ...],  # deck cards fully/partially covered
  "missing_total": 2,
}
```

- [ ] TDD + commit `feat(deck_picker): trade_report for missing vs owned`

### Task 2: Name-list export

**Files:** Create `exporters/name_list.py`; Test `tests/test_name_list_export.py`

**Interfaces:**
- `def to_arena_text(names: list[str], *, title: str = "") -> str` — collapsed counts `4 Shock`
- `def to_copy_paste(names: list[str]) -> str` — same collapsed form
- `def write_arena_file(path, names, *, title="") -> Path`

- [ ] TDD + commit `feat(exporters): arena/copy-paste from name lists`

### Task 3: League progress + polish API

**Files:** Create `league/progress.py`; Modify `league/api.py`; Tests

**Interfaces:**
- `@dataclass class JobProgress: challenges: int; best_deck_id; best_winrate; games_vs_top; league_size; forge_available: bool`
- `def snapshot_progress(job_state, league) -> JobProgress`
- API:
  - `GET /api/league/progress` — module job state if any, else zeros + forge flag
  - `POST /api/league/trade-report` — body `{deck, owned}` → trade_report
  - `POST /api/league/export` — body `{deck, format: arena|copy_paste}` → `{text}`

Keep `_LAST_JOB_STATE` updated from challenge/run endpoints.

- [ ] TDD + commit `feat(league): progress trade-report and export endpoints`

---
