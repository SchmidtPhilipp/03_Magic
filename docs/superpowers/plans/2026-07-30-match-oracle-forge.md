# Match Oracle + Forge Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `MatchOracle` adapter layer with CI-safe stub, Forge `.dck` export, headless Forge AI-vs-AI runner (env-configured), match-record persistence, and a thin HTTP endpoint — no league/Dreamer yet.

**Architecture:** New package `magic_optimizer.match_oracle` beside `deck_picker`. Callers only use `MatchOracle.play`. Default in tests/CI is `StubMatchOracle`. Production path is `ForgeMatchOracle` wrapping subprocess `java -jar $FORGE_JAR sim …` with `ForgePlayerAI` as the player backend marker. No hardcoded SSH; Homelab points Forge via env vars only.

**Tech Stack:** Python 3.11+, pytest, Flask, subprocess; optional Java/Forge on Homelab (not required for CI).

## Global Constraints

- No hardcoded hosts/SSH (`PVE_SSH` only as documented env for future workers — not used in this plan’s code paths).
- CI must never require Forge or network; use stub + recorded fixtures.
- Observe-only health: `forge_available()` returns bool; never start/restart Forge or CTs.
- Timeouts on every Forge subprocess (`FORGE_TIMEOUT_SEC`, default 300).
- Decklists are `list[CardRef]` (60 cards) from Plan 1; convert to Forge `.dck` for the runner.
- Secrets never logged; do not print jar paths with embedded credentials.
- TDD per task; `PYTHONPATH=src`; commits after each task.

## File structure

| Path | Responsibility |
|------|----------------|
| `src/magic_optimizer/match_oracle/__init__.py` | Public exports |
| `src/magic_optimizer/match_oracle/types.py` | `MatchResult`, protocols |
| `src/magic_optimizer/match_oracle/stub.py` | Deterministic stub oracle |
| `src/magic_optimizer/match_oracle/dck.py` | Arena-ish → Forge `.dck` text |
| `src/magic_optimizer/match_oracle/forge_runner.py` | Subprocess + stdout/log parse |
| `src/magic_optimizer/match_oracle/forge.py` | `ForgeMatchOracle` |
| `src/magic_optimizer/match_oracle/records.py` | JSONL match records |
| `src/magic_optimizer/match_oracle/health.py` | Observe-only availability check |
| `src/magic_optimizer/match_oracle/api.py` | Flask blueprint |
| `tests/test_match_oracle_*.py` | Unit tests + fixtures |
| `tests/fixtures/forge_sim_quiet.txt` | Sample Forge `-q` output |

---

### Task 1: Match types and protocols

**Files:**
- Create: `src/magic_optimizer/match_oracle/types.py`
- Create: `src/magic_optimizer/match_oracle/__init__.py`
- Test: `tests/test_match_oracle_types.py`

**Interfaces:**
- Consumes: `CardRef` from `magic_optimizer.deck_picker.types`
- Produces:
  - `@dataclass(frozen=True) class MatchResult: wins_a: int; wins_b: int; games_played: int; void_games: int = 0; engine: str = ""; details: str = ""` with property `winrate_a -> float` (`wins_a / games_played` or `0.0` if no games)
  - `class PlayerBackend(Protocol): name: str` (attribute only for MVP)
  - `class MatchOracle(Protocol): def play(self, deck_a: list[CardRef], deck_b: list[CardRef], *, games: int) -> MatchResult: ...`
  - `class ForgePlayerAI: name = "forge_ai"`

- [ ] **Step 1: Write failing test**

```python
from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.types import ForgePlayerAI, MatchResult


def test_winrate_a():
    r = MatchResult(wins_a=3, wins_b=1, games_played=4, engine="stub")
    assert r.winrate_a == 0.75


def test_winrate_zero_games():
    r = MatchResult(wins_a=0, wins_b=0, games_played=0)
    assert r.winrate_a == 0.0


def test_forge_player_ai_name():
    assert ForgePlayerAI().name == "forge_ai"
```

- [ ] **Step 2:** `PYTHONPATH=src pytest tests/test_match_oracle_types.py -v` → FAIL  
- [ ] **Step 3: Implement** types as above; export from `__init__.py`  
- [ ] **Step 4:** PASS  
- [ ] **Step 5: Commit** `feat(match_oracle): add MatchResult and protocols`

---

### Task 2: StubMatchOracle

**Files:**
- Create: `src/magic_optimizer/match_oracle/stub.py`
- Modify: `__init__.py`
- Test: `tests/test_match_oracle_stub.py`

**Interfaces:**
- `class StubMatchOracle:`  
  - `__init__(self, *, seed: int = 0)`  
  - `play(deck_a, deck_b, *, games: int) -> MatchResult`  
  - Deterministic: hash of sorted card names of A vs B + seed decides each game (bit of sha256); `engine="stub"`; `void_games=0`; reject `games < 1` with `ValueError`.

- [ ] **Step 1: Failing tests**

```python
from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.stub import StubMatchOracle


def test_stub_deterministic_and_counts():
    a = [CardRef("Shock")] * 60
    b = [CardRef("Bolt")] * 60
    o = StubMatchOracle(seed=1)
    r1 = o.play(a, b, games=10)
    r2 = o.play(a, b, games=10)
    assert r1 == r2
    assert r1.games_played == 10
    assert r1.wins_a + r1.wins_b == 10
    assert r1.engine == "stub"


def test_stub_rejects_zero_games():
    o = StubMatchOracle()
    try:
        o.play([CardRef("Shock")], [CardRef("Bolt")], games=0)
        assert False
    except ValueError:
        pass
```

- [ ] **Step 2–5:** implement, test, commit `feat(match_oracle): add deterministic StubMatchOracle`

---

### Task 3: Forge `.dck` writer

**Files:**
- Create: `src/magic_optimizer/match_oracle/dck.py`
- Test: `tests/test_match_oracle_dck.py`

**Interfaces:**
- `def to_dck(deck: list[CardRef], *, name: str = "Deck") -> str`  
  Forge constructed format:
  ```
  [metadata]
  Name=Deck
  [Main]
  4 Shock
  20 Island
  ...
  ```
  Aggregate counts by name; skip empty names; main section only (no sideboard).

- [ ] **Step 1: Failing test**

```python
from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.dck import to_dck


def test_to_dck_aggregates():
    deck = [CardRef("Shock"), CardRef("Shock"), CardRef("Island")]
    text = to_dck(deck, name="Test")
    assert "Name=Test" in text
    assert "[Main]" in text
    assert "2 Shock" in text
    assert "1 Island" in text
```

- [ ] **Step 2–5:** implement, commit `feat(match_oracle): write Forge .dck decklists`

---

### Task 4: Forge runner + result parser (fixture-based)

**Files:**
- Create: `src/magic_optimizer/match_oracle/forge_runner.py`
- Create: `tests/fixtures/forge_sim_quiet.txt`
- Test: `tests/test_match_oracle_forge_runner.py`

**Interfaces:**
- `def parse_forge_sim_output(text: str) -> tuple[int, int, int]` → `(wins_a, wins_b, games_played)`  
  Parse quiet-style lines. Accept patterns like:
  - `DeckA beat DeckB (3-1)` or `Game result: Player1 wins` accumulators  
  - Also accept a simple custom fixture format for CI:
    ```
    RESULT wins_a=3 wins_b=1 games=4
    ```
    Prefer supporting the `RESULT wins_a=…` line first (our runner will ask Forge to emit or we normalize). For real Forge `-q` output variability, also try regex `(\d+)\s*[-–]\s*(\d+)` on a line containing `result` or `wins` (case-insensitive). If unparsable → raise `ForgeParseError`.

- `class ForgeParseError(Exception): ...`

- `def build_forge_sim_command(*, java: str, jar: str, deck_a: str, deck_b: str, games: int, extra_args: list[str] | None = None) -> list[str]`  
  → `[java, "-jar", jar, "sim", "-d", deck_a, deck_b, "-n", str(games), "-q"]` (+ extra_args)

- `def run_forge_sim(*, java: str, jar: str, deck_dir: str, deck_a_name: str, deck_b_name: str, games: int, timeout_sec: float) -> MatchResult`  
  - Writes nothing if files already present; runs subprocess with `timeout=timeout_sec`, `capture_output=True`, `text=True`  
  - On timeout → `MatchResult(wins_a=0, wins_b=0, games_played=0, void_games=games, engine="forge", details="timeout")`  
  - On non-zero exit → void all games with `details=stderr[:500]`  
  - On success → parse stdout+stderr combined  

**Do not** call real Forge in unit tests: test `parse_forge_sim_output` with fixture file and `build_forge_sim_command` only. Optionally test `run_forge_sim` by monkeypatching `subprocess.run`.

Fixture file content:
```
RESULT wins_a=3 wins_b=1 games=4
```

- [ ] **Step 1–5:** TDD, commit `feat(match_oracle): Forge sim command builder and parser`

---

### Task 5: ForgeMatchOracle + health + records

**Files:**
- Create: `src/magic_optimizer/match_oracle/forge.py`
- Create: `src/magic_optimizer/match_oracle/health.py`
- Create: `src/magic_optimizer/match_oracle/records.py`
- Test: `tests/test_match_oracle_forge_oracle.py`, `tests/test_match_oracle_records.py`, `tests/test_match_oracle_health.py`

**Interfaces:**

`ForgeMatchOracle`:
```python
class ForgeMatchOracle:
    def __init__(
        self,
        *,
        jar: str | None = None,
        java: str = "java",
        work_dir: str | None = None,
        timeout_sec: float | None = None,
        player: ForgePlayerAI | None = None,
    ) -> None:
        ...
    def play(self, deck_a: list[CardRef], deck_b: list[CardRef], *, games: int) -> MatchResult:
        ...
```
- Reads `FORGE_JAR` / `FORGE_JAVA` / `FORGE_TIMEOUT_SEC` (default 300) / `FORGE_WORK_DIR` from env when args omitted.
- If `jar` missing → raise `RuntimeError("FORGE_JAR not set")`.
- Creates temp subdir under work_dir, writes `a.dck` / `b.dck` via `to_dck`, calls `run_forge_sim`.
- `player` stored as `self.player` (default `ForgePlayerAI()`).

`health.py`:
- `def forge_available(*, jar: str | None = None, java: str = "java") -> bool`  
  True iff jar path exists as file (from arg or `FORGE_JAR`). No process start.

`records.py`:
- `def append_match_record(path: str | Path, record: dict) -> None` — append one JSON line  
- `def match_record_from_result(deck_a_names: list[str], deck_b_names: list[str], result: MatchResult) -> dict`  
  keys: `deck_a`, `deck_b`, `wins_a`, `wins_b`, `games_played`, `void_games`, `engine`, `winrate_a`, `details`

- [ ] **Step 1:** Tests for records round-trip; health true/false with tmp path; ForgeMatchOracle with monkeypatched `run_forge_sim`  
- [ ] **Step 2–5:** implement, commit `feat(match_oracle): ForgeMatchOracle, health check, JSONL records`

---

### Task 6: Flask API

**Files:**
- Create: `src/magic_optimizer/match_oracle/api.py`
- Modify: `web_app.py` (register blueprint)
- Test: `tests/test_match_oracle_api.py`

**Interfaces:**
- Blueprint `match_oracle_bp`, prefix `/api/match-oracle`
- `POST /play` JSON:
  ```json
  {
    "deck_a": ["Shock", "..."],
    "deck_b": ["Bolt", "..."],
    "games": 3,
    "backend": "stub"
  }
  ```
  - `backend`: `"stub"` (default) or `"forge"`  
  - `200`: MatchResult as JSON (`wins_a`, `wins_b`, `games_played`, `void_games`, `engine`, `winrate_a`, `details`)  
  - `400` on bad JSON / missing decks / games < 1  
  - `503` if `backend=forge` and `not forge_available()`
- `GET /health` → `{"forge_available": bool}` (observe-only)

Register in `web_app.py` like `deck_picker_bp`.

- [ ] **Step 1–5:** TDD with minimal Flask app, commit `feat(match_oracle): expose play and health HTTP API`

---

## Out of scope (later plans)

- League / StopPolicy / optimization jobs (Plan 3)  
- Dreamer (Plan 4)  
- Homelab Docker/Komodo deploy compose for Forge jar distribution  
- LearnedPlayer  

## Plan self-review

1. Spec §10 MatchOracle/Forge/PlayerBackend/timeouts/observe-only — covered.  
2. No placeholders; stub keeps CI green.  
3. Types consistent with Plan 1 `CardRef`.
