# Homelab Self-Play Loop (League ↔ Forge/Stub ↔ Dreamer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire a closed self-play loop that bootstraps a league, plays matches via `MatchOracle` (stub in CI / Forge when available), appends match records, retrains the Dreamer world model, and builds new challengers with `DreamerNextCardPolicy` until StopPolicy fires.

**Architecture:** New `magic_optimizer.selfplay` package orchestrating existing league/dreamer/match_oracle. Pure Python; Homelab only selects `backend=forge` via env/API. No SSH, no heal.

**Tech Stack:** Python 3.11+, pytest, Flask; stub oracle in CI.

## Global Constraints

- TDD; `PYTHONPATH=src`; CI never requires Forge.
- Observe-only: if Forge requested but unavailable → clear error, do not start services.
- Match records JSONL optional path under `runs/` (gitignored).
- No hardcoded hosts/SSH.

## File structure

| Path | Responsibility |
|------|----------------|
| `src/magic_optimizer/selfplay/loop.py` | `SelfPlayLoop` |
| `src/magic_optimizer/selfplay/oracle_factory.py` | stub vs forge selection |
| `src/magic_optimizer/selfplay/api.py` | `POST /api/selfplay/run` |
| `scripts/run_selfplay_loop.py` | CLI entry |
| `tests/test_selfplay_*.py` | TDD |

---

### Task 1: Oracle factory

**Interfaces:**
- `def make_oracle(*, backend: str = "stub", seed: int = 0) -> MatchOracle`
  - `"stub"` → StubMatchOracle
  - `"forge"` → ForgeMatchOracle if `forge_available()` else raise `RuntimeError("forge unavailable")`

- [ ] TDD + commit `feat(selfplay): oracle factory stub or forge`

### Task 2: SelfPlayLoop

**Interfaces:**
```python
class SelfPlayLoop:
    def __init__(self, *, oracle, stop_policy, pool, constraints, ratings,
                 records_path=None, games_per_match=5, seed=0, retrain_every=2):
    def run(self, *, bootstrap_n: int = 3, max_challenges: int = 20) -> dict:
        # 1 seed league heuristic
        # 2 loop: build challenger (dreamer if trained else heuristic)
        # 3 challenge via OptimizationJob
        # 4 append match record from summary
        # 5 every retrain_every: fit WorldModel from buffer
        # 6 stop on policy or max
        # return {job_state, standings, model_trained, records_written}
```

- [ ] TDD with StubMatchOracle + tiny pool + commit `feat(selfplay): SelfPlayLoop league dreamer cycle`

### Task 3: API + CLI

- `POST /api/selfplay/run` — body like league/run + `backend`, `records_path`, `retrain_every`
- Register blueprint in `web_app.py`
- `scripts/run_selfplay_loop.py` — argparse, reads pool JSON or minimal demo pool, `SELFPLAY_BACKEND` env default stub

- [ ] TDD API + commit `feat(selfplay): HTTP and CLI entrypoints`

---
