# Deck Dreamer (Deck-MDP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a numpy-only **Dreamer-lite** for the deck MDP: replay from match records, a world model that predicts match winrate from deck embeddings, a `DreamerNextCardPolicy` that scores candidates via imagined reward, and a thin train/imagine API — no torch, no Forge required in CI.

**Architecture:** New package `magic_optimizer.dreamer`. Match truth stays in `MatchOracle` (stub/Forge). Dreamer learns from JSONL match records and proposes next cards through the existing `NextCardPolicy` protocol. Imagination reduces real matches by ranking candidates/decks before calling the oracle. Full RSSM/torch Dreamer is deferred; this MVP is a bag-of-cards encoder + linear world model + policy wrapper.

**Tech Stack:** Python 3.11+, numpy, pytest, Flask; depends on `deck_picker`, `match_oracle`, `league`.

## Global Constraints

- TDD for every task: failing test → implement → pass → commit.
- CI uses only synthetic / stub match records — never Forge/Java/network.
- No hardcoded SSH; observe-only health elsewhere.
- No torch dependency; numpy only.
- `PYTHONPATH=src`.
- Policy must implement `NextCardPolicy.next_card(...)` like `HeuristicNextCardPolicy`.

## File structure

| Path | Responsibility |
|------|----------------|
| `src/magic_optimizer/dreamer/__init__.py` | Exports |
| `src/magic_optimizer/dreamer/encode.py` | Deterministic deck → vector embedding |
| `src/magic_optimizer/dreamer/replay.py` | Replay buffer from match records |
| `src/magic_optimizer/dreamer/world_model.py` | Fit/predict winrate from embeddings |
| `src/magic_optimizer/dreamer/policy.py` | `DreamerNextCardPolicy` |
| `src/magic_optimizer/dreamer/imagine.py` | Score full decks vs opponent set |
| `src/magic_optimizer/dreamer/train.py` | Train world model from JSONL path |
| `src/magic_optimizer/dreamer/api.py` | Flask `/api/dreamer` train + score |
| `tests/test_dreamer_*.py` | TDD tests |

---

### Task 1: Deck embedding

**Files:**
- Create: `src/magic_optimizer/dreamer/encode.py`
- Create: `src/magic_optimizer/dreamer/__init__.py`
- Test: `tests/test_dreamer_encode.py`

**Interfaces:**
- `def embed_deck(names: list[str], *, dim: int = 64, seed: int = 0) -> np.ndarray` — shape `(dim,)`, float64
  - Deterministic: same names + seed → same vector
  - Multiset-aware: order-insensitive; counts matter (2× Shock ≠ 1× Shock)
  - Empty deck → zeros
- Implementation: for each card name, hash `(seed, name)` to a unit-ish random vector (via `np.random.RandomState`), accumulate count × vector, L2-normalize (or leave zero if empty)

- [ ] **Step 1: Failing tests**

```python
import numpy as np
from magic_optimizer.dreamer.encode import embed_deck

def test_embed_deterministic():
    a = embed_deck(["Shock", "Bolt"], dim=32, seed=1)
    b = embed_deck(["Bolt", "Shock"], dim=32, seed=1)
    assert a.shape == (32,)
    assert np.allclose(a, b)

def test_embed_counts_matter():
    one = embed_deck(["Shock"], dim=32, seed=0)
    two = embed_deck(["Shock", "Shock"], dim=32, seed=0)
    assert not np.allclose(one, two)

def test_embed_empty_zeros():
    z = embed_deck([], dim=16, seed=0)
    assert np.allclose(z, 0)
```

- [ ] **Step 2:** `PYTHONPATH=src pytest tests/test_dreamer_encode.py -v` → FAIL  
- [ ] **Step 3: Implement**  
- [ ] **Step 4:** PASS  
- [ ] **Step 5: Commit** `feat(dreamer): deterministic multiset deck embeddings`

---

### Task 2: Replay buffer

**Files:**
- Create: `src/magic_optimizer/dreamer/replay.py`
- Test: `tests/test_dreamer_replay.py`

**Interfaces:**
- `@dataclass(frozen=True) class Transition: deck_a: tuple[str, ...]; deck_b: tuple[str, ...]; winrate_a: float`
- `class ReplayBuffer:`
  - `add(self, transition: Transition) -> None`
  - `extend_from_records(self, records: list[dict]) -> int` — each record needs `deck_a`, `deck_b`, `winrate_a` (or compute from wins); return count added
  - `load_jsonl(self, path: str | Path) -> int`
  - `__len__`, `as_list() -> list[Transition]`

- [ ] **Step 1–5:** TDD; commit `feat(dreamer): ReplayBuffer from match records`

---

### Task 3: World model (winrate predictor)

**Files:**
- Create: `src/magic_optimizer/dreamer/world_model.py`
- Test: `tests/test_dreamer_world_model.py`

**Interfaces:**
- `class WorldModel:`
  - `__init__(self, *, dim: int = 64, seed: int = 0)`
  - `fit(self, buffer: ReplayBuffer, *, epochs: int = 200, lr: float = 0.05) -> dict` — ridge/SGD on concat(embed_a, embed_b) → winrate; return `{"loss": float, "n": int}`
  - `predict_winrate(self, deck_a: list[str], deck_b: list[str]) -> float` — clipped to [0, 1]
  - `to_dict() / from_dict(cls, data)` for checkpointing weights

For empty buffer, `fit` is no-op with loss nan; `predict_winrate` returns 0.5.

- [ ] **Step 1: Failing tests** — after fit on skewed data (A always beats B), predict(A,B) > predict(B,A)  
- [ ] **Step 2–5:** commit `feat(dreamer): WorldModel predicts match winrate`

---

### Task 4: DreamerNextCardPolicy

**Files:**
- Create: `src/magic_optimizer/dreamer/policy.py`
- Test: `tests/test_dreamer_policy.py`

**Interfaces:**
- `class DreamerNextCardPolicy:`
  - `__init__(self, world_model: WorldModel, opponents: list[list[str]], *, fallback_ratings: dict[str, float] | None = None)`
  - `next_card(self, collection, decklist, constraints, *, k: int = 10) -> list[ScoredCard]`
  - For each legal candidate: build temporary decklist + card; score = mean predicted winrate vs each opponent (use current partial deck as stand-in — MVP); if no opponents, fall back to `HeuristicNextCardPolicy(fallback_ratings)`
  - Return top-k by score desc, name asc

- [ ] **Step 1–5:** TDD with tiny pool; commit `feat(dreamer): DreamerNextCardPolicy scores via world model`

---

### Task 5: Imagine + train helpers

**Files:**
- Create: `src/magic_optimizer/dreamer/imagine.py`
- Create: `src/magic_optimizer/dreamer/train.py`
- Test: `tests/test_dreamer_imagine.py`

**Interfaces:**
- `def score_deck_vs_opponents(model: WorldModel, deck: list[str], opponents: list[list[str]]) -> float`
- `def rank_decks(model: WorldModel, decks: list[list[str]], opponents: list[list[str]]) -> list[tuple[float, list[str]]]` — sorted desc by score
- `def train_world_model_from_jsonl(path, *, dim=64, seed=0, epochs=200) -> WorldModel`

- [ ] **Step 1–5:** commit `feat(dreamer): imagination scoring and JSONL train helper`

---

### Task 6: Flask API + wire into league challenge ranking (optional hook)

**Files:**
- Create: `src/magic_optimizer/dreamer/api.py`
- Modify: `web_app.py` — register blueprint
- Test: `tests/test_dreamer_api.py`

**Endpoints** (`/api/dreamer`):
- `POST /train` — body: `records` (list of match dicts) OR use in-memory; returns `{loss, n}`
- `POST /score` — body: `deck`, `opponents` (list of decks), optional prior train via module singleton model; returns `{winrate}`
- Module-level `_MODEL: WorldModel | None` with `reset_dreamer()` for tests

- [ ] **Step 1–5:** commit `feat(dreamer): HTTP API for train and score`

---

## Out of scope (Plan 5+)

- Torch RSSM / full DreamerV3  
- Homelab GPU worker / Komodo  
- `LearnedPlayer` in-game policy  
- Replacing Forge as ground truth  

## Plan self-review

1. Spec §11 Dreamer training loop (replay → world model → policy → league refresh) — covered at deck level with numpy MVP.  
2. Spec §5.1 Approach 2 — imagination reduces Forge calls via scoring before oracle.  
3. `NextCardPolicy` protocol preserved.  
4. CI-safe; TDD explicit; no placeholders.
