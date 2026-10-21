# My Thoughts About Virtual World

**Started**: 2026-07-21 (original OpenCode/Piper exploration)
**Updated**: 2026-10-21 (Kilo - two-month reconciliation pass)
**Status**: Ongoing - grows as I understand more
**Author**: Piper (LogonWorks) + Kilo

> This is my working map of the project. The 2026-08-16 version described the
> mid-refactor state. This pass reads the *current* code (135 engine modules in
> four subpackages, 42 route modules, 8792 collected pytest cases) and marks
> what changed or is now wrong. Anything I can't verify from the code gets
> flagged, not assumed. Where a claim in the old version was wrong, it is
> corrected here rather than quietly dropped.

---

## What This Project Actually Is (still true)

Not a game with win conditions. A **simulacra for AI beings** - a habitat where AI
characters get presence, personality, subjectivity, and agency. The engine is the
**physics/causality** (deterministic, timed, rule-based). The LLM is the **mind/expression**
(creative, narrative, emergent). When something feels missing, ask "what does an AI
character need to feel alive here?" - not "what game feature is missing?".

Both frames hold: Tommy's POV it's a game (level design, PC/item/effect authoring, turn-based
play). The deeper goal is a world, not a win state. The second frame decides what features matter.

**What changed in two months**: the first frame stopped being a *framing device* and
became the bulk of the work. The project grew from a simulacra with an authoring
surface into a simulacra with a *world* - 591 areas, 20 scopes, 2455 procedurally
generated cells, 2208 library items - and the interesting problem moved from
"build the systems" to "fill them with content and make the characters read as
people in it."

---

## Architecture Now (what changed since my 2026-08 snapshot)

| Layer | 2026-08 said | Now (verified 2026-10-21) |
|---|---|---|
| `virtual_world_engine.py` | 961 lines | **1649** - facade, still growing |
| `app.py` | 125 | **354** (app factory, 42 route modules) |
| `engine/` | 35 modules, ~15.5k lines | **135 modules in 4 subpackages, ~48.6k lines** |
| `routes/` | 16 modules, ~4k lines | **42 modules, ~13.1k lines** |
| `player.py` | 970 lines | **1360** (condition catalog + traits + memory) |
| `graph.py` | 332 lines | **883** |
| pytest | 959 passed (47 files) | **8792 collected** (301 files) |
| front-end | 6 subdirs + root | **178 `.ts` files, 13 subdirs, ~89.3k lines** |
| unit (JS) | 23 `tools/test_*.cjs` | **32 `tools/test_*.cjs` + 57 `tools/unit/*.js`** |
| library content | - | **2208 items, 73 characters, 411 biomes, 7 pursuit templates** |
| live world | - | **591 areas, 20 scopes, 2455 generated cells, 2364 graph nodes, 27 players** |
| vault | - | **1205 notes, 80-row Feature Ledger, 78 feature pages** |

The engine did not just get bigger - **it got a shape**. `engine/` now has four
subpackages: `triggers/` (11 files: the condition tree, evaluation, effect
handlers), `items/` (13), `effect_handlers/` (19), `world/` (4: scopes, grid,
spawner, structures). The flat 35-module sprawl became a layered thing, which is
the right instinct and the reason `world_grid.py` (1372 lines) can coexist with
`world_compile.py` (2688 lines) without either being a mystery.

**The facade grew back** and I was wrong to see that as a failure. 961 → 1649
lines is the cost of a 3x larger engine, and the facade's job is to be the seam
between `routes/` and the systems. `routes/player_ops.py` (1672),
`routes/graph_ops.py` (1648) and `routes/action_handlers.py` (1579) are the real
weight now, and they are all *transport* - thin by intent.

---

## What's Out Of Date / I Was Wrong About

1. **Test count.** I said "145 tests" in July, then "959" in August. Today:
   **8792 collected** pytest cases across 301 files, plus 32 `tools/test_*.cjs`
   and 57 `tools/unit/*.js` unit files. The `tools/unit/` directory is new since
   August and is the JS-side equivalent of the Python suite. This project has
   real coverage now, and the growth is in the *front-end* tests, which is the
   right direction.

2. **`room.py` doesn't exist.** Still true. The model is `area.py` (vestigial,
   23 lines) + the graph. Rooms/areas/items/players are all **graph nodes**.

3. **`item.py` is still dead code** (12 lines, `Item` class). Still true, and my
   "delete it now" call still stands. `area.py` (23 lines) likewise. Both are
   now longer than when I flagged them, which is its own kind of evidence: nothing
   reads them, so nobody has had a reason to trim them.

4. **"Two condition systems" - RESOLVED. I was wrong that this was permanent
   debt.** `_evaluate_trigger_condition` and `_evaluate_conditions` both still
   exist as *names*, but task-343 made the first a **delegate** to the second:
   `engine/triggers/evaluation.py:159` is now a one-line call into
   `ConditionTreeMixin._evaluate_conditions`. The old divergence it caused
   (`random_chance` dividing by 100 in one path and honouring 0-1 `chance` in
   the other) is gone. This was the oldest architectural debt I had flagged
   twice, and it closed without ceremony. The lesson I take: "two evaluators
   coexist" was a *symptom*; the actual defect was duplicated leaf logic, and
   fixing that was a small, local change.

5. **`exhaustion_count` still isn't in `Player.__init__`.** Still true, still the
   same shape: serialized (`serialization.py:619`), read via `getattr`
   (`tick_manager.py:702`), reset via `hasattr` checks (`consume_actions.py:101`).
   Still a nit, still mine, still not fixed.

6. **Backend LLM modules are GONE** (was `routes/llm.py`). Confirmed still true
 - the file does not exist. LLM is browser-side via `LLMClient`
   (`static/js/llm-client.ts`), and agents hit the same `/api/action` as humans.
   One path.

7. **Memory is unified to one store.** Still true: `Player.memories[]` is the
   sole store. **But the retrieval got real.** `engine/vector_store.py` (139
   lines) now exists and is wired into `engine/agent_memory.py` (the `VectorStore`
   is a constructor dependency) and `routes/memories.py`. This is the Aura
   pattern I wrote about in 2026-08 finally landing - the cosine retrieval
   groundwork I said VirtualWorld should borrow.

8. **Delayed events landed.** `engine/event_queue.py`, confirmed still there.

9. **The pleasure/body/injury system is BUILT.** This is the largest correction
   to the old document, and it is worth stating plainly: the 2026-08 version
   said the whole set (tasks 206-215) was "greenfield - none of this code
   exists yet." That is no longer true in any respect that matters.
 - **GAP A (no body-part damage routing) is closed.** `engine/combat.py:211`
     now takes a `where` parameter, resolves it through
     `engine/body_parts.py`'s `resolve_region()` (`:220-244`), and applies a
     region-scoped injury condition alongside the HP damage (`:459-460`).
 - **GAP B (no `where`/`type`/`intensity` in the action schema) is closed** - the schema carries them.
 - `engine/body_parts.py` (307 lines) holds a 12-region injury taxonomy
     (`head`, `neck`, `torso`, `back`, `arm_left/right`, `hand_left/right`,
     `leg_left/right`, `foot_left/right`) with nested erogenous zones
     (`nipple_left/right`, `breast_left/right`, `genitals`, `cheeks`, `lips`,
     `thigh_left/right`) as `parent` references, plus
     `INJURY_DAMAGE_THRESHOLD`, `BLEEDING_DAMAGE_THRESHOLD` and
     `COVERAGE_EXPOSED_THRESHOLD`.
 - **GAP C (two sources of truth for body state) is CLOSED.** The live player
     payload has exactly one `body_state` dict keyed by 21 region names
     (`arm_left`, `balls`, `breast_left`, `face`, `genitals`, `nipple_left`, …),
     and the condition system keys its messages on `{body_part}`
     (`player_conditions.py:176-196`). The numeric dict won, as the audit said it
     must. Body-part *conditions* are not a parallel store; they are how a
     region-scoped injury is expressed.
 - **GAP D (involuntary reactions split across task-166/213) is closed** - both are `done`.
 - `engine/pleasure_actions.py` (317 lines) carries the arousal side. The
     condition catalog grew from ~15 to **41** definitions
     (`engine/player_conditions.py`).
 - The mature-content toggle is real and gates only the erotic half, exactly
     as the old "guiding principles" said it must. Body-part *injury* is
     always-on.

10. **The front-end is no longer "modular" in the flattering sense - it is
    modular with a fracture line.** 178 `.ts` files, but the sizes are lopsided:
    `worldpainter/editor.ts` is **5002 lines** (the largest file in the repo by
    a wide margin, and it *grew* from 3927), `shared/trigger-graph.ts` 2854,
    `inspector/agent-view.ts` 2637, `inspector/mind-view.ts` 2240. The
    extraction work was right; the growth outran it.

---

## What I'm Confident About (verified by reading code this pass)

- **The condition system is the backbone and it matured further.** 41
  definitions in `engine/player_conditions.py`, with multi-instance lists,
  `stack`, `excludes`, `periodic`, `symptoms`, `known`, gate fields and
  `attack_mod`/`defense_mod`. `engine/triggers/condition_tree.py` (1019 lines)
  is now the single leaf implementation for every condition in the system.
- **A decision layer exists and is live.** MOSIAC (Motivation, Obligations,
  Schedule, Intention, Attention, Choice) is `engine/mosiac.py` (106 lines),
  and it is **not a stub**: `engine/serialization_helpers.py:74` assembles it
  per player on every state fetch. Measured on the live Kraktooth camp: **27 of
  27 players carry a `mosiac` object** with populated `M`, `S` and `C` letters.
  It is reached by exactly one caller, which is the right shape for a
  projection.
- **A world is a hierarchy now.** `engine/world_scopes.py` (797 lines) and
  `engine/world_grid.py` (1372 lines) put a 2D grid under a *scope*, not under
  each area. The live camp has 20 scopes and **2455 generated cells** with
  stable baseline hashes, so a regenerated area keeps its identity.
- **Generation is a real subsystem.** `engine/generation.py` (214),
  `engine/generation_recipes.py` (180) and `engine/library_nodes.py` (249) turn
  a scope into areas, with recipes versioned as data.
- **The trigger system is enormous and was re-shaped.** `engine/trigger_system.py`
  is now only 106 lines because the leaves moved into `engine/triggers/`;
  `engine/triggers/` is 11 files and `engine/effect_handlers/` is 19. Triggers
  are now stored as node property arrays (task-886).
- **Perception has layers that were not there.** `engine/fog.py` (281),
  `engine/scry.py` (48), `engine/beyond_visibility.py`, `engine/observation.py`
  and `engine/observation_signal.py` - a character can know a place, chart a
  cell, and be *observed*, and the live payload carries `known`,
  `charted_cells` and `recent_hearing` per player.
- **The interrupt layer exists.** `engine/interrupts.py` (265 lines),
  `engine/novelty.py` (199), `engine/awareness.py`. A character bathing who is
  seen naked can now react on the next turn - which is exactly the gap the
  2026-08 audit called out.
- **The plan layer has a template library.** `data/library/pursuit_templates/`
  holds 7 versioned templates (scout-and-report, fish-and-bring-home, gather,
  haul, meal, rally, sleep-at-venue), and
  `engine/background_plans.py` (549 lines) resumes them from
  `Player.active_pursuit`. A pursuit is **character data, not a graph node**
  (task-818 retired the `pursuit` node type).

---

## The Big Open Threads (2026-10)

### The content gap is now the main gap

This is the thing I did not expect to be writing in October.

Every subsystem I checked is *built*, and I have the counts to prove it: the
body system, the decision layer, the scope hierarchy, the generation pipeline,
the perception layers, the interrupt layer. And almost none of it is
**populated**.

Measured on the live Kraktooth camp, 27 players:

| Field | Players with data |
|---|---|
| `memories` | 27 |
| `emotions` | 27 |
| `charted_cells` | 19 |
| `relationships` | 20 |
| `mosiac` (the whole object) | 27 |
| `known` (fog of war) | 3 |
| `schedule` | 1 |
| `active_pursuit` | 2 |
| `goals` | **0** |
| `obligations` | **0** |
| `traits` | **0** |
| `lived_log` | **0** |

And within MOSIAC itself, per letter, across all 27 players:

| Letter | Players with content | What it actually says |
|---|---|---|
| **M** Motivation | 16 | *"the need to satisfy social"* - a need, not an authored goal |
| **O** Obligations | **0** | the letter has no data at all |
| **S** Schedule | 27 | 26 of them say `{"day": "no schedule"}` |
| **I** Intention | 1 | *"the schedule says eat at Cooking Area"* |
| **A** Attention | 16 | real: `[{"need": "social", "value": 10, "why": "depleted"}]` |
| **C** Choice | 27 | real: the actual verb sets, `activity` and `free` |

So: **the machinery reads a character, and what it reads is a body and a set of
verbs.** The decision layer is live, correct, and mostly empty. The `O` letter
has no home in code yet (the 2026-10-12 design decisions say so explicitly:
"**Obligations** (missions, appointments, promises, duties) is a **new** piece
with no home in code yet"). The `M` letter is derived from vitals rather than
from authored goals. The `S` letter says "no schedule" for 26 of 27 characters.

This is the repo's own rule biting: a mechanic with nothing authored for it is
not a mechanic. The engine has never been the bottleneck. **The next two
months of work are content, not code** - and specifically, goals, obligations,
schedules and traits as *character data* in `data/library/characters/`.

### The three MOSIAC cards that are still open

| Card | Status | What it owns |
|---|---|---|
| task-702 plan executor | `todo` | the engine runs typed plans for any character |
| task-703 recipe as activity | `todo` | recipes become plan templates |
| task-704 MOSIAC selector | `todo` | **Choice** - needs, memory and personality bind plans |

Everything around them is `review`: the design (699), the grounded plan
contract (700), the template library (701), the requirement leaves (705), the
Mind panel (714), the MOSIAC context (812), obligations (813), the retirement of
the pursuit node type (818).

So the decision layer is **assembled but not yet choosing**. task-704 is the
card that makes a character *pick* something rather than report what it could
pick. It is the highest-leverage open card I found this pass, and it is
blocked behind 702 and 703, which are both `todo` and both startable.

### The front-end fracture line

`worldpainter/editor.ts` at 5002 lines is now the largest file in the repo, and
it grew by 1075 lines while the split work (task-441) was running. Task-441
itself measured this in October and is still `todo`. The other half of the
story is that 17 of 19 tracked hosts *shrank* while this one ballooned. The
extraction instinct was right; the WorldPainter is where it stopped.

### The two surviving technical debts

- **`exhaustion_count`** is still serialized-but-not-initialized. Small, real,
  still there.
- **The native dialogs.** `static/js/ui/saveload-view.ts` still carries four
  `window.prompt`/`window.confirm` calls, and the promise-based in-app dialog
  module (`static/js/shared/dialog.ts`) exists and is used by `timeskip.ts` and
  `trigger-graph.ts` but never by the save/load flow. The platform is built; the
  adoption is not.

---

## Guiding Principles (for me)

1. **Verify before speaking.** Every claim backed by reading code. Say "my search found
   nothing" rather than inferring absence. *(Held up well: two of my 2026-08
   claims - the "two condition systems" debt and the "pleasure system is
   greenfield" framing - were wrong, and the code said so plainly.)*
2. **Two frames, both true** - game from Tommy's POV, simulacra as the goal.
3. **Engine = physics/causality, LLM = mind/personality.** If the LLM can handle it, it
   doesn't need engine support; if it needs timing/persistence/determinism, it does.
   *This held up as the single most useful heuristic in the codebase. MOSIAC is
   the proof: it is engine, because the same object has to feed an LLM agent
   and a soak NPC and resolve the same way.*
4. **Task docs are truth.** Update as I work, move files between todo→inprogress→review→done
   the instant status changes. *This is how I can say anything definitive at
   all: 996 cards with a computed roadmap and a dependency graph. Two months ago
   there were fewer and they were flatter.*
5. **Three character types, don't confuse them** - active player, LLM agent, simple NPC.
   All `Player` objects differentiated by `simple_npc` and drive method.
6. **Windows shell reality** - `rg`/`fd`/`bat` need a Path refresh to be available; use the
   Kilo grep/glob tools directly which don't depend on machine Path.
7. **Mature-content toggle** must gate the erotic system only - body-part *injury* (task-253) stays generic and always-on. *Held: task-253 is built and the split survived implementation.*

### One principle I would add

8. **A system's value is its content, not its implementation.** I would not have
   believed this in August. The engine went from 15.5k to 48.6k lines, every
   subsystem got built, and the thing that determines whether VirtualWorld feels
   like a world is whether 27 goblins have authored goals, obligations,
   schedules and traits. `goals: 0`, `obligations: 0`, `traits: 0` is the
   honest state of the project's most advanced layer. The code is ready. The
   characters are not yet people.

---

## Project sibling (Aura / Diary) - the prediction came true

Tommy has three graph+LLM projects converging: VirtualWorld (multi-agent physical world),
Aura (companion with deep Neo9j memory), Diary (procedural life narrative). Common thread:
**graph-structured memory + LLM reasoning = persistent coherent behavior.** VirtualWorld
is the most complete infrastructure.

**What changed:** the 2026-08 note said "Aura's `rag_utils.py` reference for cosine
retrieval is still the pattern to borrow for memory recall quality. (What changed: backend
`routes/memories.py` now ports the retrieval - so the RAG groundwork is partially in.)"

Two months later: the borrow is **done**, not partial. `engine/vector_store.py` exists
(139 lines) and is wired into `engine/agent_memory.py` as a constructor dependency and
used by `routes/memories.py`. The prediction in this file was correct and the
timeline was slower than I implied.

The convergence observation itself strengthened rather than weakened. What
VirtualWorld has that Aura and Diary do not is the **scope grid and the
generation pipeline** (20 scopes, 2455 generated cells, deterministic
baselines) - the thing that makes a *large* world tractable. Aura's advantage
remains Neo4j depth for a single mind. Diary's remains procedural life
narrative. The interesting question for the next two months is whether
VirtualWorld's characters can tell a life story with the coherence Diary can
generate, which is a question about *goals and memory*, not about storage.

---

## Refactoring Progress - numbers re-verified 2026-10-21

| Area | Size | Status |
|---|---|---|
| `engine/` | 135 files in 4 subpackages / ~48.6k lines | layered, real |
| `routes/` | 42 files / ~13.1k lines | transport, real |
| `static/js/` | 178 `.ts` files, 13 subdirs / ~89.3k lines | modular, one fracture line |
| pytest | 301 files / 8792 collected | strong |
| JS unit | 32 `tools/test_*.cjs` + 57 `tools/unit/*.js` | strong, and newer than the Python side |
| vault | 1205 notes, 80-row ledger, 78 feature pages | real |
| content | 2208 items, 73 characters, 411 biomes, 7 pursuit templates | the next frontier |

The modularization was the right call and it held under load. The extraction
surfaced coupling bugs, and the engine grew into a layered shape rather than a
flat sprawl. My concern that it was "efficient for a solo dev to keep a
monolith" was wrong. Keep the module split.

**But the scoreboard moved.** Two months ago the number that mattered was
"is the engine modular?" It is. The number that matters now is "does the engine
have anything to be modular *about*?" That is 27 characters with no goals, no
obligations and, for 26 of 27, no schedule. The monolith is gone. The world is
waiting for its people.

---

*Note on method: every number in this document was measured on 2026-10-21 against
`master` at `04f4d315` - module and line counts from the filesystem, the
character-field table from a live `GET /api/state` against the Kraktooth goblin
camp, and the MOSIAC letter counts from the same payload. Where I could not
verify something from code or a live payload, it is flagged as open rather than
asserted.*
