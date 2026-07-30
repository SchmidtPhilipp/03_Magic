# Spec Review: Deck Dreamer Self-Play

**Date:** 2026-07-30  
**Spec:** `docs/superpowers/specs/2026-07-30-deck-dreamer-selfplay-design.md`

## Verdict

Spec is coherent and implementable as a phased program. MVP boundaries (deck-level Dreamer, Forge AI as player, Approach-3 adapter) are clear. No blockers.

## Findings (non-blocking)

| # | Severity | Finding | Resolution for Plan 1 |
|---|----------|---------|------------------------|
| 1 | Note | Spec spans 6 phases (picker → Forge → league → Dreamer → polish → learned player). One mega-plan would violate bite-sized / no-placeholder rules. | **Plan 1 = foundation only** (constraints, `next_card`, heuristic, pool resolve, missing cards, thin API). Plans 2–4 follow. |
| 2 | Low | Cube persistence schema not specified (only logical entity). | Defer cube table to Plan 2; Plan 1 supports personal + in-memory union of collections. |
| 3 | Low | Non-basic target default 40 is a starting point; Constructed land counts vary. | Config constant `DEFAULT_NON_BASIC_TARGET = 40`; tunable later. |
| 4 | Low | Heuristic ranking without 17Lands still needs a score. | Plan 1: optional rating map `dict[str, float]`; missing → 0.0; stable name tie-break. |
| 5 | Info | Dual DeckPolicy A/B optional in spec. | League dual-policy deferred to Plan 3; single policy + candidates is enough for Plan 1. |

## Spec → Plan mapping

| Spec section | Plan |
|--------------|------|
| §4 Constraints, §7 NextCard API, §8 lands, §4.2 missing cards, §12 CardPool | **Plan 1 (this)** |
| §10 MatchOracle / Forge Homelab | Plan 2 |
| §9 League / StopPolicy / jobs | Plan 3 |
| §11 Dreamer | Plan 4 |
| §5.2 LearnedPlayer | Plan 5 |

---

# Deck Picker Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a generalized autoregressive `next_card(collection, decklist, constraints)` API with ban/pin enforcement, personal/union pools, deterministic basic-land completion, and a missing-card trade report — heuristic backend only.

**Architecture:** New package `magic_optimizer.deck_picker` with pure domain types and functions (no Flask/Forge inside). Web route is a thin adapter. Heuristic policy ranks legal candidates by optional rating map. Dreamer/Forge plug in later behind the same `NextCardPolicy` protocol.

**Tech Stack:** Python 3.11+, existing `magic_optimizer` package, pytest, Flask (existing `web_app.py` / collection routes pattern).

## Global Constraints

- Deck size target: **60**; max copies per card name: **4** (also capped by pool availability).
- Basics (Plains, Island, Swamp, Mountain, Forest): **unlimited** and never require pool membership.
- Banlist cards never appear in candidates; pinned cards must already be in `decklist` or are prepended by the caller before calling `next_card`.
- `next_card` is the **only** deck-building entry point for suggestions; no parallel “emit full deck” API in this plan.
- No Forge, no Dreamer, no Homelab worker in this plan.
- No hardcoded SSH hosts; no secrets in code.
- TDD: failing test → implement → pass → commit per task.
- Follow existing import style: `from magic_optimizer...` (package under `src/`).

## File structure

| Path | Responsibility |
|------|----------------|
| `src/magic_optimizer/deck_picker/__init__.py` | Public exports |
| `src/magic_optimizer/deck_picker/types.py` | `CardRef`, `DeckConstraints`, `CardPool`, `ScoredCard` |
| `src/magic_optimizer/deck_picker/candidates.py` | Legal next-card filtering |
| `src/magic_optimizer/deck_picker/heuristic.py` | `HeuristicNextCardPolicy` |
| `src/magic_optimizer/deck_picker/complete.py` | Roll full deck + basic land fill |
| `src/magic_optimizer/deck_picker/missing.py` | Missing-card report vs ownership |
| `src/magic_optimizer/deck_picker/pools.py` | Build `CardPool` from collection card rows |
| `src/magic_optimizer/deck_picker/api.py` | Flask blueprint `deck_picker` |
| `tests/test_deck_picker_*.py` | Unit tests per module |

---

### Task 1: Domain types

**Files:**
- Create: `src/magic_optimizer/deck_picker/types.py`
- Create: `src/magic_optimizer/deck_picker/__init__.py`
- Test: `tests/test_deck_picker_types.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `CardRef(name: str)` — frozen dataclass; equality/hash by normalized name
  - `BASIC_LANDS: frozenset[str]` = `{"Plains", "Island", "Swamp", "Mountain", "Forest"}`
  - `DeckConstraints(deck_size: int = 60, max_copies: int = 4, banned: frozenset[str] = frozenset(), pinned: tuple[str, ...] = (), non_basic_target: int = 40)`
  - `CardPool` — holds `available: dict[str, int]` (name → max copies in pool); method `copies_available(name: str) -> int` (basics → `10**9`)
  - `ScoredCard(card: CardRef, score: float)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_deck_picker_types.py
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
    ScoredCard,
)


def test_card_ref_normalizes_and_hashes():
    a = CardRef(" Lightning Bolt ")
    b = CardRef("Lightning Bolt")
    assert a.name == "Lightning Bolt"
    assert a == b
    assert hash(a) == hash(b)


def test_card_pool_basics_unlimited():
    pool = CardPool({"Shock": 2})
    assert pool.copies_available("Shock") == 2
    assert pool.copies_available("Island") >= 10**6
    assert "Island" in BASIC_LANDS


def test_deck_constraints_defaults():
    c = DeckConstraints()
    assert c.deck_size == 60
    assert c.max_copies == 4
    assert c.non_basic_target == 40
    assert c.banned == frozenset()
    assert c.pinned == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/PhilippSchmidt/Documents/cursor/03_Magic && PYTHONPATH=src pytest tests/test_deck_picker_types.py -v`  
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

```python
# src/magic_optimizer/deck_picker/types.py
from __future__ import annotations

from dataclasses import dataclass, field

BASIC_LANDS: frozenset[str] = frozenset(
    {"Plains", "Island", "Swamp", "Mountain", "Forest"}
)


@dataclass(frozen=True)
class CardRef:
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())


@dataclass(frozen=True)
class DeckConstraints:
    deck_size: int = 60
    max_copies: int = 4
    banned: frozenset[str] = field(default_factory=frozenset)
    pinned: tuple[str, ...] = ()
    non_basic_target: int = 40


@dataclass
class CardPool:
    available: dict[str, int]

    def copies_available(self, name: str) -> int:
        if name in BASIC_LANDS:
            return 10**9
        return int(self.available.get(name, 0))


@dataclass(frozen=True)
class ScoredCard:
    card: CardRef
    score: float
```

```python
# src/magic_optimizer/deck_picker/__init__.py
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
    ScoredCard,
)

__all__ = [
    "BASIC_LANDS",
    "CardPool",
    "CardRef",
    "DeckConstraints",
    "ScoredCard",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_deck_picker_types.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/magic_optimizer/deck_picker/types.py src/magic_optimizer/deck_picker/__init__.py tests/test_deck_picker_types.py
git commit -m "feat(deck_picker): add domain types for next-card API"
```

---

### Task 2: Legal candidates

**Files:**
- Create: `src/magic_optimizer/deck_picker/candidates.py`
- Modify: `src/magic_optimizer/deck_picker/__init__.py`
- Test: `tests/test_deck_picker_candidates.py`

**Interfaces:**
- Consumes: `CardPool`, `DeckConstraints`, `CardRef` from Task 1
- Produces: `def legal_candidates(pool: CardPool, decklist: list[CardRef], constraints: DeckConstraints) -> list[CardRef]`

Rules:
- Count copies already in `decklist` by name.
- Exclude banned names (normalize strip).
- Exclude names where `copies_in_deck >= min(constraints.max_copies, pool.copies_available(name))`.
- If `len(decklist) >= constraints.deck_size`, return `[]`.
- Do not auto-insert pins here (caller owns pins in decklist).
- Basics are legal even if absent from `pool.available`.
- Return sorted by name for determinism.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_deck_picker_candidates.py
from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints


def test_excludes_banned_and_respects_copies():
    pool = CardPool({"Shock": 4, "Bolt": 1, "Cancel": 4})
    deck = [CardRef("Bolt")]
    constraints = DeckConstraints(banned=frozenset({"Cancel"}), max_copies=4)
    names = [c.name for c in legal_candidates(pool, deck, constraints)]
    assert "Cancel" not in names
    assert "Bolt" not in names  # only 1 available
    assert "Shock" in names


def test_full_deck_yields_empty():
    pool = CardPool({"Shock": 4})
    deck = [CardRef("Shock")] * 60
    assert legal_candidates(pool, deck, DeckConstraints()) == []


def test_basics_always_available():
    pool = CardPool({"Shock": 4})
    names = [c.name for c in legal_candidates(pool, [], DeckConstraints())]
    assert "Island" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_deck_picker_candidates.py -v`  
Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/magic_optimizer/deck_picker/candidates.py
from __future__ import annotations

from collections import Counter

from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
)


def legal_candidates(
    pool: CardPool,
    decklist: list[CardRef],
    constraints: DeckConstraints,
) -> list[CardRef]:
    if len(decklist) >= constraints.deck_size:
        return []

    counts = Counter(c.name for c in decklist)
    banned = {b.strip() for b in constraints.banned}

    names: set[str] = set(pool.available.keys()) | set(BASIC_LANDS)
    result: list[CardRef] = []
    for name in sorted(names):
        if name in banned:
            continue
        limit = min(constraints.max_copies, pool.copies_available(name))
        if counts[name] >= limit:
            continue
        if limit <= 0:
            continue
        result.append(CardRef(name))
    return result
```

Export `legal_candidates` from `__init__.py`.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=src pytest tests/test_deck_picker_candidates.py tests/test_deck_picker_types.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/magic_optimizer/deck_picker/candidates.py src/magic_optimizer/deck_picker/__init__.py tests/test_deck_picker_candidates.py
git commit -m "feat(deck_picker): filter legal next-card candidates"
```

---

### Task 3: Heuristic NextCardPolicy

**Files:**
- Create: `src/magic_optimizer/deck_picker/heuristic.py`
- Modify: `src/magic_optimizer/deck_picker/__init__.py`
- Test: `tests/test_deck_picker_heuristic.py`

**Interfaces:**
- Consumes: `legal_candidates`
- Produces:
  - `class NextCardPolicy(Protocol)` with `next_card(self, collection: CardPool, decklist: list[CardRef], constraints: DeckConstraints, *, k: int = 10) -> list[ScoredCard]`
  - `class HeuristicNextCardPolicy` with `__init__(self, ratings: dict[str, float] | None = None)` and `next_card(...)` ranking by rating (default 0.0), higher first; tie-break name ascending; return top `k`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_deck_picker_heuristic.py
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import CardPool, CardRef, DeckConstraints


def test_ranks_by_rating_and_respects_k():
    pool = CardPool({"A": 4, "B": 4, "C": 4})
    policy = HeuristicNextCardPolicy({"A": 1.0, "B": 3.0, "C": 2.0})
    top = policy.next_card(pool, [], DeckConstraints(), k=2)
    assert [s.card.name for s in top] == ["B", "C"]
    assert top[0].score == 3.0


def test_skips_banned():
    pool = CardPool({"A": 4, "B": 4})
    policy = HeuristicNextCardPolicy({"A": 9.0, "B": 1.0})
    top = policy.next_card(
        pool, [], DeckConstraints(banned=frozenset({"A"})), k=5
    )
    assert all(s.card.name != "A" for s in top)
    assert top[0].card.name == "B"
```

- [ ] **Step 2: Run to verify fail**

Run: `PYTHONPATH=src pytest tests/test_deck_picker_heuristic.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# src/magic_optimizer/deck_picker/heuristic.py
from __future__ import annotations

from typing import Protocol

from magic_optimizer.deck_picker.candidates import legal_candidates
from magic_optimizer.deck_picker.types import (
    CardPool,
    CardRef,
    DeckConstraints,
    ScoredCard,
)


class NextCardPolicy(Protocol):
    def next_card(
        self,
        collection: CardPool,
        decklist: list[CardRef],
        constraints: DeckConstraints,
        *,
        k: int = 10,
    ) -> list[ScoredCard]:
        ...


class HeuristicNextCardPolicy:
    def __init__(self, ratings: dict[str, float] | None = None) -> None:
        self._ratings = ratings or {}

    def next_card(
        self,
        collection: CardPool,
        decklist: list[CardRef],
        constraints: DeckConstraints,
        *,
        k: int = 10,
    ) -> list[ScoredCard]:
        scored = [
            ScoredCard(card=c, score=float(self._ratings.get(c.name, 0.0)))
            for c in legal_candidates(collection, decklist, constraints)
        ]
        scored.sort(key=lambda s: (-s.score, s.card.name))
        return scored[: max(0, k)]
```

Export `HeuristicNextCardPolicy`, `NextCardPolicy` from `__init__.py`.

- [ ] **Step 4: Run tests** — expect PASS  
- [ ] **Step 5: Commit** — `feat(deck_picker): add heuristic next-card policy`

---

### Task 4: Deck completion + basic land fill

**Files:**
- Create: `src/magic_optimizer/deck_picker/complete.py`
- Modify: `src/magic_optimizer/deck_picker/__init__.py`
- Test: `tests/test_deck_picker_complete.py`

**Interfaces:**
- Consumes: `NextCardPolicy` / `HeuristicNextCardPolicy`, types
- Produces:
  - `def count_non_basics(decklist: list[CardRef]) -> int` — cards whose name not in `BASIC_LANDS`
  - `def fill_basics(decklist: list[CardRef], constraints: DeckConstraints, color_pips: dict[str, int] | None = None) -> list[CardRef]` — append basics until `deck_size`; if `color_pips` is None or all zero, use equal split in WUBRG order (Plains, Island, Swamp, Mountain, Forest); deterministic
  - `def complete_deck(policy: HeuristicNextCardPolicy, pool: CardPool, constraints: DeckConstraints, *, seed_deck: list[CardRef] | None = None) -> list[CardRef]` — start from pins in `constraints.pinned` plus `seed_deck`, greedily take `policy.next_card(..., k=1)[0]` until `non_basic_target` or no candidates; then `fill_basics`

- [ ] **Step 1: Failing tests**

```python
# tests/test_deck_picker_complete.py
from magic_optimizer.deck_picker.complete import complete_deck, fill_basics
from magic_optimizer.deck_picker.heuristic import HeuristicNextCardPolicy
from magic_optimizer.deck_picker.types import (
    BASIC_LANDS,
    CardPool,
    CardRef,
    DeckConstraints,
)


def test_fill_basics_reaches_sixty_deterministically():
    deck = [CardRef("Shock")] * 40
    out = fill_basics(deck, DeckConstraints())
    assert len(out) == 60
    assert sum(1 for c in out if c.name in BASIC_LANDS) == 20
    assert fill_basics(deck, DeckConstraints()) == out


def test_complete_deck_includes_pins_and_size():
    pool = CardPool({f"Card{i}": 4 for i in range(50)})
    ratings = {f"Card{i}": float(i) for i in range(50)}
    constraints = DeckConstraints(
        pinned=("Card49",),
        non_basic_target=40,
        banned=frozenset(),
    )
    policy = HeuristicNextCardPolicy(ratings)
    deck = complete_deck(policy, pool, constraints)
    assert len(deck) == 60
    assert deck[0].name == "Card49" or any(c.name == "Card49" for c in deck)
    assert sum(1 for c in deck if c.name not in BASIC_LANDS) == 40
```

- [ ] **Step 2: Run — expect FAIL**  
- [ ] **Step 3: Implement** `complete.py` per interfaces above (pins first in deck order, then greedy next_card).  
- [ ] **Step 4: Tests PASS**  
- [ ] **Step 5: Commit** — `feat(deck_picker): complete decks with deterministic basics`

---

### Task 5: Pools from collections + missing cards

**Files:**
- Create: `src/magic_optimizer/deck_picker/pools.py`
- Create: `src/magic_optimizer/deck_picker/missing.py`
- Modify: `src/magic_optimizer/deck_picker/__init__.py`
- Test: `tests/test_deck_picker_pools_missing.py`

**Interfaces:**
- Consumes: `CardPool`, `CardRef`
- Produces:
  - `def pool_from_card_rows(rows: list[dict]) -> CardPool` — aggregate by `card_name` summing `amount` (int); skip empty names
  - `def union_pools(*pools: CardPool) -> CardPool` — sum availability per name
  - `def missing_cards(deck: list[CardRef], owned: CardPool) -> list[tuple[str, int]]` — for each non-basic name, `needed = count_in_deck - owned.copies_available(name)` if positive; return sorted `(name, needed)` list

- [ ] **Step 1: Failing tests**

```python
from magic_optimizer.deck_picker.missing import missing_cards
from magic_optimizer.deck_picker.pools import pool_from_card_rows, union_pools
from magic_optimizer.deck_picker.types import CardPool, CardRef


def test_pool_from_rows_and_union():
    a = pool_from_card_rows(
        [{"card_name": "Shock", "amount": 2}, {"card_name": "Shock", "amount": 1}]
    )
    assert a.copies_available("Shock") == 3
    b = CardPool({"Bolt": 2, "Shock": 1})
    u = union_pools(a, b)
    assert u.copies_available("Shock") == 4
    assert u.copies_available("Bolt") == 2


def test_missing_cards_ignores_basics():
    owned = CardPool({"Shock": 1})
    deck = [CardRef("Shock"), CardRef("Shock"), CardRef("Island"), CardRef("Bolt")]
    miss = missing_cards(deck, owned)
    assert miss == [("Bolt", 1), ("Shock", 1)]
```

- [ ] **Step 2–5:** implement, test, commit — `feat(deck_picker): pool union and missing-card report`

---

### Task 6: Thin Flask API

**Files:**
- Create: `src/magic_optimizer/deck_picker/api.py`
- Modify: `web_app.py` (register blueprint) **or** `src/magic_optimizer/collection/routes.py` pattern — prefer new blueprint registered in `web_app.py` where other blueprints are registered
- Test: `tests/test_deck_picker_api.py` (Flask test client)

**Interfaces:**
- `POST /api/deck-picker/next-card` JSON body:
  ```json
  {
    "pool": {"Shock": 4, "Bolt": 2},
    "decklist": ["Shock"],
    "banned": ["Bolt"],
    "pinned": [],
    "ratings": {"Shock": 2.0},
    "k": 5
  }
  ```
- Response `200`: `{"candidates": [{"name": "Shock", "score": 2.0}, ...]}`  
- Invalid JSON / missing pool → `400`

Also `POST /api/deck-picker/complete` with same pool/constraints/ratings → `{"deck": ["...", ...], "missing": [["Name", 1], ...]}` where missing is vs `owned` object if provided else empty.

Inspect `web_app.py` for how `collection` blueprint is registered and mirror that.

- [ ] **Step 1: Write API tests with Flask test client** (create app factory or import app; if app hard to import, test the view functions with a minimal Flask app that registers the blueprint only).  
- [ ] **Step 2: Fail**  
- [ ] **Step 3: Implement blueprint + register**  
- [ ] **Step 4: Pass**  
- [ ] **Step 5: Commit** — `feat(deck_picker): expose next-card and complete HTTP API`

---

## Follow-up plans (not in this plan)

- **Plan 2:** Forge `MatchOracle` adapter + Homelab worker smoke  
- **Plan 3:** League, StopPolicy, optimization jobs  
- **Plan 4:** Dreamer world model on deck MDP  
- **Plan 5:** `LearnedPlayer` backend  

## Plan self-review

1. **Spec coverage (Plan 1):** §4 constraints, §7 API, §8 lands, §4.2 missing, §12 pool — yes. Forge/Dreamer/league — explicitly deferred.  
2. **Placeholders:** none intentional.  
3. **Types:** `CardRef` / `CardPool` / `DeckConstraints` / `ScoredCard` consistent across tasks.
