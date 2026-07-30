# Design: Deck Dreamer Self-Play Optimizer

**Date:** 2026-07-30  
**Status:** Draft for review  
**Project:** 03_Magic (MTG Sealed/Constructed Deck Optimizer)

## 1. Goal

Build a deck optimizer that finds strong Constructed decks for a growing, limited card pool shared by a small playgroup (~5 players), using **self-play** and **model-based RL (Dreamer)** on the **deck-construction** level.

**Primary outcome:** Given a card pool and constraints, produce decks that meet a measurable strength target (default: winrate threshold against a league of opponents), with optional trade guidance when the user does not yet own every card.

**Non-goal (MVP):** A neural net that plays individual game actions. Gameplay in matches is Forge’s built-in AI. A learned in-game player is a later upgrade path (Approach 3).

## 2. Context (current system)

Today the app optimizes sealed-style decks with heuristic algorithms (greedy, genetic, simulated annealing) and static evaluators (manual ratings, 17Lands-style scores). There is no rules engine, no match simulation, and no RL.

This design **extends** that stack: keep collection management and UI as the front door; add a Homelab training worker, Forge match oracle, league self-play, and a generalized next-card deck policy.

## 3. Format and rules

| Rule | Decision |
|------|----------|
| Match format | Standard 1v1 (playgroup always plays 1v1) |
| Deck size | 60 cards |
| Copies | Max 4 of a card, limited by availability in the chosen pool |
| Basic lands | Unlimited additional basic lands (W/U/B/R/G as needed) |
| Extra rules | None |
| Ownership | A player may play only cards from their collection **or** from an agreed larger pool when trading is in scope |
| Trading | Allowed — optimizing a deck the user does not fully own is a first-class use case |

## 4. Card pools and constraints

### 4.1 Pool modes

Resolved `CardPool` for a job is one of:

1. **Personal** — one player’s collection only.  
2. **Union** — union of all registered collections (trade-aware building).  
3. **Cube+Union** — shared set-based cube (grows with each set) **union** selected collections; collections still track ownership for the missing-card report.

Mode is chosen per optimization job. Cube cards without an owner still appear in the legal pool when mode 3 is selected.

### 4.2 Soft ownership

When building from union/cube, the result may include cards the user lacks. The job output lists **missing cards** vs. a selected personal collection (trade checklist).

### 4.3 Hard constraints (always applied before candidates are scored)

- **Banlist** — cards that must never appear.  
- **Pinned / must-include** — cards fixed in the decklist before or during building.  
- Copy limits and pool membership.  
- Target deck size (60); basics filled after the non-basic skeleton (see §8).

Constraints are part of the job config and hashed into league entries so results are comparable only under the same constraint set (or explicitly cross-evaluated).

## 5. Chosen approach

### 5.1 MVP: Approach 2 — Dreamer on the Deck-MDP + Forge as match oracle

- **State:** card pool embedding + current partial decklist + constraint flags.  
- **Action:** choose the next card (from legal candidates).  
- **Reward:** match outcomes from Forge (win/loss, optionally margin/stats).  
- **World model (Dreamer):** learns latent dynamics of deck-vs-deck strength so many “imagined” continuations reduce the number of real Forge matches.  
- **Players inside Forge:** Forge built-in AI for both seats.

### 5.2 Path to Approach 3

`MatchOracle` and `PlayerBackend` are interfaces:

- MVP: `ForgePlayerAI`  
- Later: `LearnedPlayer` (policy over game actions), without rewriting the deck loop

Full Dreamer-over-game-tree remains out of MVP scope; the adapter boundary is what makes the upgrade possible.

### 5.3 Optional Phase-0 bootstrap

Existing genetic / simulated annealing optimizers (with proxy scores or early Forge fitness) seed the first league population before the Dreamer policy is strong.

## 6. Architecture

```text
[Web App] ── job + pool + constraints ──► [Homelab Worker]
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │  Deck optimization loop │                         │
                    │                         ▼                         │
                    │              NextCardPolicy (Dreamer)             │
                    │                 │              │                  │
                    │            Deck A ◄──league──► Deck B             │
                    │                 │              │                  │
                    │                 └──────┬───────┘                  │
                    │                        ▼                         │
                    │              MatchOracle (adapter)                │
                    │                        │                         │
                    │           ┌────────────┴────────────┐            │
                    │           ▼                         ▼            │
                    │    ForgePlayerAI (MVP)      LearnedPlayer (later)│
                    │           │                         │            │
                    │           └────────────┬────────────┘            │
                    │                        ▼                         │
                    │              MatchResult → Replay Buffer          │
                    │                        │                         │
                    │                        ▼                         │
                    │         WorldModel update + StopPolicy           │
                    └──────────────────────────────────────────────────┘
```

**Deployment:** Training and Forge batch matches run on the **Homelab** (Docker/LXC/Komodo-style worker). The web app starts jobs, shows progress, and presents results; it does not run long Forge batches in-process.

## 7. Generalized Deck Picker (core API)

The deck builder is **not** “emit 60 cards at once”. It is an **autoregressive next-card picker** (LLM-like completion over decklists).

```text
next_card(collection, decklist, constraints) → ranked_candidates
```

| Input | Meaning |
|-------|---------|
| `collection` | Legal pool for this call (personal or union/cube) |
| `decklist` | Current list (0…60); pins already present |
| `constraints` | Bans, max copies, size target, etc. |

| Output | Meaning |
|--------|---------|
| `ranked_candidates` | Legal next cards with scores (policy / imagined winrate delta) |

**Uses**

- **Interactive:** User builds card-by-card; UI asks for the next suggestion.  
- **Self-play rollouts:** Agent fills a deck by calling `next_card` repeatedly with exploration.  
- **Dreamer imagination:** Roll forward in latent space without Forge; periodically correct with real matches.

Pinned cards start in `decklist`. Banned cards never appear in candidates. Basics may be suggested by a separate land-fill step once the non-land skeleton is set (see §8).

### 7.1 Interface sketch (Python)

```python
class NextCardPolicy(Protocol):
    def next_card(
        self,
        collection: CardPool,
        decklist: list[CardRef],
        constraints: DeckConstraints,
        *,
        k: int = 10,
    ) -> list[ScoredCard]:
        """Return top-k legal next cards for this partial deck."""
        ...
```

Implementations: heuristic baseline → Dreamer-backed policy → future fine-tuned variants. Call sites depend only on this protocol.

## 8. Deck completion and lands

1. Build via `next_card` until the deck reaches a configured **non-basic target** (default: 40 cards that are not basic lands — pins count toward this). Non-basic lands from the pool may be chosen in this phase.  
2. **Basic land filler:** add unlimited basics to reach exactly 60, using a deterministic curve/color heuristic (extend existing land logic). Same skeleton ⇒ same basics ⇒ reproducible Forge matches.  
3. Validate final 60-card list against constraints.  
4. Export Arena/MTGO-compatible list using existing exporters where possible.

## 9. League, alternating decks, self-play

### 9.1 League

Persistent population of decks:

- Decklist  
- Rating (Elo or similar)  
- Constraint/pool hash  
- Provenance (bootstrap vs self-play generation)  
- Aggregate match stats  

### 9.2 Duel loop

1. Challenger policy rolls deck \(D_A\) via `next_card`.  
2. Opponent is sampled from the league (Elo-nearby or champion).  
3. `MatchOracle` runs Best-of-N with Forge AI.  
4. Update ratings; promote/relegate.  
5. Store transitions in a replay buffer for world-model and policy learning.  

**Alternating decks:** There are not two fixed forever-decks. A **challenge queue** rotates who is challenger vs league member. Both logical “agents” share learning signal from the same buffer (symmetric self-play). Optional dual-policy training (A/B parameters) is allowed but not required for MVP if a single policy + league opponents is enough.

### 9.3 StopPolicy (pluggable)

```text
StopPolicy.should_stop(job_state) -> bool
```

| Implementation | Behavior |
|----------------|----------|
| **WinrateThreshold (default)** | Stop when best deck’s winrate ≥ threshold over N matches vs Top-k league |
| `EloPlateau` | Stop when rating improvement stays below ε for M evaluations |
| `ManualReview` | Stop only on user cancel / explicit accept |

Defaults (configurable): e.g. threshold 0.55, N ≥ 20, Top-k = 5 — exact numbers tuned in implementation plan / config.

## 10. MatchOracle and Forge

### 10.1 Adapter

```python
class PlayerBackend(Protocol):
    """How seats make in-game decisions. MVP: Forge AI. Later: LearnedPlayer."""
    ...

class MatchOracle(Protocol):
    def play(self, deck_a: Decklist, deck_b: Decklist, *, games: int) -> MatchResult:
        ...
```

`MatchOracle` owns engine + `PlayerBackend` (both seats). Callers never talk to Forge or a learned player directly. `MatchResult` includes wins/losses per side, optional turn counts / game length, and engine metadata.

### 10.2 Default engine: Forge

- Homelab worker invokes Forge in headless/batch mode.  
- Decklists converted to Forge-readable format.  
- Timeouts and retries; failed games do not crash the job (logged, excluded or retried).  
- Observe-only health checks for “is Forge worker up”; healing is out of band (homelab ops).

### 10.3 Swap path

XMage or another engine can implement `MatchOracle` later. Learned players implement `PlayerBackend` behind the same oracle.

## 11. Dreamer training (deck level)

**What is modeled:** Transition structure over (pool, partial deck, next card) and predicted match outcomes vs opponent decks — not full MTG game trees in MVP.

**Loop (high level):**

1. Collect real matches (Forge) into replay.  
2. Train world model on latent dynamics + reward prediction.  
3. Improve `NextCardPolicy` via imagined rollouts + occasional real evaluation.  
4. Refresh league with newly rolled decks.  
5. Evaluate StopPolicy.

**Compute:** Homelab GPU/CPU as available; Forge matches are the scarce resource — imagination exists to spend them wisely.

## 12. Data model (logical)

| Entity | Role |
|--------|------|
| `Player` / collection | Existing collection store; import large CSVs |
| `Cube` / set overlay | Optional shared growing pool |
| `CardPool` | Resolved legal set for a job |
| `DeckConstraints` | Bans, pins, size, copy limits |
| `OptimizationJob` | Config, status, progress, result refs |
| `LeagueDeck` | Population member + rating |
| `MatchRecord` | Oracle results for training/eval |
| `ModelCheckpoint` | World model + policy versions |

Large collection import = first-class: bulk CSV/API into collections/cube without treating it as a separate ML corpus.

## 13. Web / product surfaces (MVP)

- Start Homelab job: pool mode, bans, pins, stop policy params.  
- Interactive `next_card` suggestions (even before full self-play is trained — heuristic backend).  
- Job progress (matches played, current best winrate, league size).  
- Results: top decks, match stats, missing-cards vs personal collection.  
- Export via existing Arena/MTGO/HTML paths.

## 14. Error handling and ops

- Illegal deck construction: reject before Forge.  
- Forge timeout/crash: retry with backoff; mark match void.  
- Job cancel: cooperative stop between matches.  
- Worker unreachable: fail job with clear error (no CI “heal” of production Forge).  
- Secrets/SSH: Homelab targets via env (`PVE_SSH` etc.), no hardcoded hosts in app code.

## 15. Testing strategy

| Layer | Tests |
|-------|-------|
| Constraints | Unit: bans, pins, copy limits, pool membership |
| Next-card API | Unit: candidates exclude bans; pins preserved; determinism of land fill |
| MatchOracle | Integration against Forge fixture or recorded stub in CI |
| League / StopPolicy | Unit: promote/relegate, threshold stop |
| End-to-end | Homelab smoke: small pool, few games, job completes |

CI must **not** depend on unbounded SSH or starting production CTs; use stubs/mocks for Forge in default CI, real Forge only on Homelab verify jobs that observe.

## 16. Success criteria

- User can import a large collection/cube and run an optimization job on Homelab.  
- User can pin and ban cards and choose personal vs union pool.  
- `next_card(collection, decklist, constraints)` is the single deck-building entry point for UI and self-play.  
- Self-play league improves decks under **WinrateThreshold** StopPolicy (default).  
- Missing-card report supports trade planning.  
- Swapping `PlayerBackend` to a learned player later does not require redesigning the deck loop.

## 17. Out of scope (MVP)

- Neural in-game action policy (Approach 3 implementation).  
- True multiplayer (FFA) training.  
- Full Dreamer over raw Forge game states.  
- Automatic trading marketplace between players.  
- Guaranteeing a globally “perfect” deck — only measurable strength vs current league under StopPolicy.

## 18. Implementation phases (preview)

1. **Constraints + NextCard protocol + heuristic backend** wired to UI.  
2. **Forge MatchOracle** on Homelab + match records.  
3. **League + WinrateThreshold jobs** (heuristic rollouts + Forge fitness).  
4. **Dreamer world model + policy** on deck MDP; imagination loop.  
5. **Polish:** trade missing-card report, exports, monitoring.  
6. **Later:** `LearnedPlayer` behind MatchOracle (Approach 3).

Detailed task breakdown belongs in the implementation plan after this spec is approved.

## 19. Decisions log

| Topic | Decision |
|-------|----------|
| Format | Constructed-ish 60, max 4, unlimited basics, 1v1, no extras |
| Pool | Cube + collections; personal or union (trades OK) |
| Constraints | Banlist + pinned cards |
| Match truth | Full rules via Forge (default), adapter for swaps |
| Self-play | Pure 1v1 league; alternating via challenge queue |
| RL | Dreamer on deck MDP; Forge AI plays games |
| Deck API | Autoregressive `next_card` |
| Stop | Pluggable; default winrate threshold |
| Compute | Homelab worker |
| “Large dataset” | Large collection/cube import, not an external ML corpus |
| Future | Path to learned in-game agent without rewriting deck loop |
