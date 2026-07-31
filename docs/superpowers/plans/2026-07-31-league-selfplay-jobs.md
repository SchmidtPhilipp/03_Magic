# League Self-Play + Optimization Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-play **league** of decks, pluggable **StopPolicy** (default WinrateThreshold), and an **OptimizationJob** runner that challenges new decks (from `NextCardPolicy` / seed) against the league via `MatchOracle` (stub in CI), persists state, and exposes a thin HTTP API — paving the way for Dreamer (Plan 4).

**Architecture:** New package `magic_optimizer.league` using `CardRef` decks and `MatchOracle.play`. Jobs are pure Python (no Homelab SSH). Default oracle in tests is `StubMatchOracle`. Elo updates after each challenge; StopPolicy decides when to halt.

**Tech Stack:** Python 3.11+, pytest, Flask; depends on `deck_picker` + `match_oracle`.

## Global Constraints

- TDD for every task: failing test → implement → pass → commit.
- CI uses `StubMatchOracle` only; never require Forge/Java/network.
- No hardcoded SSH; no healing production.
- Decks are `list[CardRef]`; league stores names + Elo + stats.
- Default StopPolicy: winrate ≥ **0.55** over ≥ **20** games vs Top-**5** (configurable).
- Elo: start **1000**, K=**32**, standard logistic.
- `PYTHONPATH=src`.

## File structure

| Path | Responsibility |
|------|----------------|
| `src/magic_optimizer/league/types.py` | `LeagueDeck`, `JobState`, Elo helpers |
| `src/magic_optimizer/league/elo.py` | Elo update math |
| `src/magic_optimizer/league/store.py` | In-memory + JSON persist league |
| `src/magic_optimizer/league/stop_policy.py` | `StopPolicy` protocol + implementations |
| `src/magic_optimizer/league/job.py` | `OptimizationJob` challenge loop |
| `src/magic_optimizer/league/api.py` | Flask blueprint |
| `src/magic_optimizer/league/__init__.py` | Exports |
| `tests/test_league_*.py` | TDD tests |

---

### Task 1: Elo math

**Files:**
- Create: `src/magic_optimizer/league/elo.py`
- Create: `src/magic_optimizer/league/__init__.py`
- Test: `tests/test_league_elo.py`

**Interfaces:**
- `def expected_score(rating_a: float, rating_b: float) -> float` — `1 / (1 + 10 ** ((rating_b - rating_a) / 400))`
- `def update_elo(rating_a: float, rating_b: float, score_a: float, *, k: float = 32.0) -> tuple[float, float]` — returns `(new_a, new_b)` where `score_a` is 1.0 win / 0.0 loss / 0.5 draw

- [ ] **Step 1: Failing tests**

```python
from magic_optimizer.league.elo import expected_score, update_elo


def test_expected_equal_ratings():
    assert abs(expected_score(1000, 1000) - 0.5) < 1e-9


def test_update_elo_winner_gains():
    a2, b2 = update_elo(1000, 1000, 1.0, k=32)
    assert a2 > 1000
    assert b2 < 1000
    assert abs((a2 - 1000) - (1000 - b2)) < 1e-9
```

- [ ] **Step 2:** `PYTHONPATH=src pytest tests/test_league_elo.py -v` → FAIL  
- [ ] **Step 3: Implement**  
- [ ] **Step 4:** PASS  
- [ ] **Step 5: Commit** `feat(league): add Elo expected score and update`

---

### Task 2: LeagueDeck + League store

**Files:**
- Create: `src/magic_optimizer/league/types.py`
- Create: `src/magic_optimizer/league/store.py`
- Modify: `__init__.py`
- Test: `tests/test_league_store.py`

**Interfaces:**
- `@dataclass class LeagueDeck: id: str; cards: list[str]; elo: float = 1000.0; wins: int = 0; losses: int = 0; games: int = 0; provenance: str = "bootstrap"`
  - `property def winrate(self) -> float`
- `class League:`
  - `__init__(self)` empty
  - `add(self, deck: LeagueDeck) -> None`
  - `get(self, deck_id: str) -> LeagueDeck`
  - `top(self, k: int) -> list[LeagueDeck]` by elo desc
  - `sample_opponent(self, *, exclude_id: str | None = None, rng: random.Random | None = None) -> LeagueDeck` — prefer among top half by elo if size≥2, else any other
  - `record_match(self, winner_id: str, loser_id: str, *, games: int, wins_winner: int, wins_loser: int, k: float = 32.0) -> None` — update elo + counters
  - `to_dict(self) / from_dict(cls, data) / save_json(path) / load_json(path)`

- [ ] **Step 1: Failing tests** for add/top/record_match/roundtrip JSON  
- [ ] **Step 2–5:** implement, commit `feat(league): League store with Elo match recording`

---

### Task 3: StopPolicy

**Files:**
- Create: `src/magic_optimizer/league/stop_policy.py`
- Test: `tests/test_league_stop_policy.py`

**Interfaces:**
- `@dataclass class JobState: best_deck_id: str | None; best_winrate: float; games_vs_top: int; elo_history: list[float]; cancelled: bool = False`
- `class StopPolicy(Protocol): def should_stop(self, state: JobState) -> bool: ...`
- `class WinrateThresholdStop:` `__init__(self, *, threshold: float = 0.55, min_games: int = 20)` — stop when `games_vs_top >= min_games and best_winrate >= threshold`
- `class EloPlateauStop:` `__init__(self, *, epsilon: float = 5.0, window: int = 5)` — stop when last `window` elo deltas all have abs < epsilon (need history length ≥ window+1)
- `class ManualReviewStop:` stop only if `state.cancelled`

- [ ] **Step 1: Failing tests** for each policy  
- [ ] **Step 2–5:** commit `feat(league): pluggable StopPolicy with winrate default`

---

### Task 4: OptimizationJob challenge loop

**Files:**
- Create: `src/magic_optimizer/league/job.py`
- Test: `tests/test_league_job.py`

**Interfaces:**
- `class OptimizationJob:`
  - `__init__(self, league: League, oracle: MatchOracle, stop_policy: StopPolicy, *, games_per_match: int = 5, seed: int = 0)`
  - `def challenge(self, cards: list[str], *, deck_id: str | None = None, provenance: str = "challenger") -> dict`  
    1. Add challenger as `LeagueDeck` (if new)  
    2. Sample opponent (exclude self)  
    3. `oracle.play` with `CardRef` lists, `games=games_per_match`  
    4. Decide winner by wins_a vs wins_b (ties: no elo change, still count games)  
    5. `record_match` if not tie  
    6. Evaluate challenger winrate vs current top-k (play extra eval matches OR accumulate from challenges — for MVP: track running `wins/games` on the deck object as overall league winrate)  
    7. Update `JobState`; return summary dict with ids, result, `should_stop`
  - `def run_until_stop(self, build_deck: Callable[[], list[str]], *, max_challenges: int = 50) -> JobState`  
    Loop: build_deck → challenge → break if stop or max

Use `StubMatchOracle` in tests with fixed seed for determinism.

- [ ] **Step 1: Failing tests** — empty league raises; one bootstrap + challenger updates elo; stop when threshold met (configure low threshold/min_games for test)  
- [ ] **Step 2–5:** commit `feat(league): OptimizationJob challenge loop`

---

### Task 5: Bootstrap + heuristic challenger helper

**Files:**
- Create: `src/magic_optimizer/league/bootstrap.py`
- Test: `tests/test_league_bootstrap.py`

**Interfaces:**
- `def deck_from_policy(policy, pool, constraints, *, seed_deck=None) -> list[str]` — calls `complete_deck`, returns names
- `def seed_league_from_pool(league, policy, pool, constraints, *, n: int, rng) -> list[str]` — add `n` decks with varied ratings noise / random seeds via `HeuristicNextCardPolicy` copies with jittered ratings; return ids

- [ ] **Step 1–5:** TDD, commit `feat(league): bootstrap league from NextCardPolicy`

---

### Task 6: Flask API

**Files:**
- Create: `src/magic_optimizer/league/api.py`
- Modify: `web_app.py`
- Test: `tests/test_league_api.py`

**Endpoints** (prefix `/api/league`):
- `POST /bootstrap` — body: `pool`, `ratings`, `n`, `constraints` fields → creates league, returns `{deck_ids, size}`
- `POST /challenge` — body: `deck` (list[str]), `games` optional; uses in-process league store (module singleton for MVP) + stub oracle unless `backend=forge` and available
- `GET /standings` — top decks elo/winrate
- `POST /run` — body: `pool`, `ratings`, `max_challenges`, `stop` `{threshold, min_games}` → `run_until_stop` with heuristic builder; return final standings + job state

Keep league in module-level `_LEAGUE: League | None` with `reset` query for tests.

- [ ] **Step 1–5:** TDD with minimal Flask app, commit `feat(league): HTTP API for bootstrap challenge and run`

---

## Out of scope (Plan 4+)

- Dreamer world model / imagination  
- LearnedPlayer  
- Homelab worker process / Komodo  
- Replay buffer for neural training  

## Plan self-review

1. Spec §9 League/StopPolicy/duel — covered.  
2. Uses MatchOracle from Plan 2.  
3. TDD explicit per task; no placeholders.
