# Plan — Dev-task worktree parallelisation

**Date:** 2026-09-28
**Scope:** map every actionable dev task to the files it touches, decide what can
genuinely run in parallel, and lay out Agent Manager worktree lanes.
**Method:** parsed all 272 actionable task files, extracted file references (full paths
plus bare filenames resolved against a repo index), classified each file by merge risk,
and partitioned by the cost of cross-lane collisions.

---

## 1. What the data says

| Measure | Value |
|---|---|
| Actionable task files | **272** (100 todo, 9 inprogress, 163 review) |
| Work queue (todo + inprogress) | **109** |
| Conflicting task pairs in the queue | **454** of 5,886 possible (7.7%) |
| Pairs sharing a *high-risk* file | **218** |
| Queued tasks touching **no** hub file | **57** (52%) |
| Queued tasks touching at least one hub | **52** (48%) |
| Serialisation edges (explicit `Depends on`) | **14** |
| Files claimed by both the review and todo queues | **130** |

The headline: **the conflicts are not spread out, they are concentrated.** A handful of
files cause almost all of them.

| Hub file | Queued tasks | Review tasks | Why it is a hub |
|---|---|---|---|
| `engine/tick_manager.py` | 13 | 12 | the turn loop — every behavioural change lands here |
| `engine/serialization.py` | 10 | 10 | save/load — any new persisted field lands here |
| `virtual_world_engine.py` | 9 | 18 | the facade nearly every feature imports |
| `routes/library_ops.py` | 9 | 2 | library schema + every registry write path |
| `routes/action_handlers.py` | 8 | 4 | the action dispatch table |
| `player.py` | 5 | 7 | ability scores and the player record |
| `routes/action.py` | 1 | 15 | action route registration |
| `app.py` | 1 | 6 | Flask app factory and route registration |

Two more files are touched constantly but are **append-only**, so concurrent edits merge
almost cleanly and they should *not* be treated as hubs:

- `templates/index.html` (28 tasks — a list of `<script>` tags)
- `tools/unit/run.cjs` (36 tasks — the module list at the top of the runner)

---

## 2. Blockers to fix before any worktree exists

These are cheap, and skipping them wastes the whole effort.

1. **The working tree is dirty.** Nine files are modified and uncommitted
   (`app.py`, `engine/world_compile.py`, `engine/world_scopes.py`,
   `routes/world_grid_ops.py`, `static/js/worldpainter/editor.js`,
   `data/scenarios/kraktooth_goblin_camp.json`, the Eldenford background, and two test
   files). Agent Manager creates each worktree from a committed base, so every lane
   would fork from a base that does not include the Eldenford work. **Commit or stash
   that work on `master` first.**
2. **There is no `.kilo/setup-script.ps1`.** `node_modules/` is gitignored, so a fresh
   worktree has no dependencies and `npm run lint`, `npm run typecheck` and
   `npm run unit` all fail. A worktree cannot clear its own gate without this.
3. **There is no `.kilo/run-script.ps1`.** Without it the Run button opens a config
   prompt instead of starting the app, so nobody can smoke-test a lane.
4. **One orphaned worktree already exists** (`.kilo/worktrees/radial-number`, detached
   HEAD). Decide whether to adopt or remove it before adding more.

---

## 3. Recommended shape: one spine, three arms

Not "N worktrees of tasks". The data supports **one serial spine plus parallel arms that
touch no hubs**.

```
                    ┌─────────────────────────────────────────┐
                    │  SPINE  WT-0  "hubs + world scale"       │
                    │  serial. 397 → 398 → 400 → 401 → 402     │
                    │  merges LAST, owns the 8 hub files       │
                    └───────────────┬─────────────────────────┘
                                    │ hub changes are pulled in
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
 ┌──────┴───────┐           ┌───────┴──────┐            ┌───────┴──────┐
 │  WT-A        │           │  WT-B        │            │  WT-C        │
 │  perception  │           │  items &     │            │  characters  │
 │  & world     │           │  inventory   │            │  & social    │
 │  16 tasks    │           │  9 tasks     │            │  11 tasks     │
 └──────────────┘           └──────────────┘            └──────────────┘
        merge first ───────────────┴──────────────────────────► merge, then spine
```

### WT-0 — Spine: hubs and world scale *(serial, 1 lane)*

The only lane allowed to edit the eight hub files. Everything else merges into it.

**The critical path, strictly in this order** (these 14 dependency edges are real):

| # | Task | Title | Blocked by |
|---|---|---|---|
| 1 | task-397 | World scopes, hierarchy manifest, server graph | — |
| 2 | task-398 | Deterministic scoped structure generation | 397 |
| 3 | task-400 | Pines vertical slice for grouped generation | 397, 398 |
| 4 | task-401 | Chunk persistence, scoped indexes, gateway ways | 397, 400 |
| 5 | task-402 | Large-world projection and indexing benchmark | 397 |
| 6 | task-409 | Background schedules, daily reflection | 408 |
| 7 | task-414 | Server-side batch time advance | 409, 411 |
| 8 | task-416 | Area-major tick iteration | — |
| 9 | task-418 | Awareness channels — audibility replaces `radius_hops` | 416 |
| 10 | task-419 | Relational spatial model — one `at` per character | 416 |
| 11 | task-426 | Plan archetypes and group goals | 409 |
| 12 | task-569 | Biome resource distribution consumer | 504 |

Because 416 (area-major tick iteration) gates 418 and 419, and 397 gates four others,
**this lane is a queue, not a parallel set.** Running it across two worktrees would just
create conflict resolution work.

Also worth knowing: three queued tasks are blocked by things *outside* the work queue —
task-407 (graph edge indexing) blocks three others, task-553 (per-area temperature)
blocks one, task-53 (in review) blocks one. Those need promoting into the queue first.

### WT-A — Perception and world presentation *(parallel, 16 tasks)*

Touches `engine/sound.py`, `engine/lighting.py`, `engine/room_perception.py`,
`engine/area_description.py`, `engine/biomes.py` — **no hub files**. Highest priority
density in the queue (6 high-priority tasks).

task-400, task-401, task-402, task-419, task-422 are *not* here — they are spine work.

Highest value: task-418 (awareness channels), task-419 (relational spatial model),
task-499 (per-agent fog of war), task-411 (attention budget / fidelity tiers),
task-550 (faction and ownership as tags).

### WT-B — Items and inventory *(parallel, 9 tasks)*

Touches `engine/equipment.py`, `engine/toggleable_items.py`, `engine/crafting.py`,
`data/library/items/` — no hub files. Includes two refactor tasks that are effectively
data migrations and are safe to run alongside feature work.

task-490, task-504, task-505 are spine (504 gates 569).

### WT-C — Characters and social *(parallel, 11 tasks)*

Touches `engine/npc_behaviors.py`, `engine/background_social.py`,
`engine/speech.py`, `static/js/agent/prompt-builder/*` — no hub files.

Includes the two open speech bugs (bug-28, bug-29) which are cheap wins and are
currently blocked on finding a live repro.

---

## 4. The review backlog is the bigger prize

**163 tasks sit in `review`.** That is 1.5× the size of the todo queue, and it is
already-written work waiting on a decision.

- 45 of them touch a hub file (18 claim `virtual_world_engine.py`, 15 claim
  `routes/action.py`).
- 21 have no resolvable file footprint at all — those are cheap to close.
- **130 files are claimed by both queues.** That is the real risk: reviewing a task can
  invalidate a queued task that assumed the old behaviour.

Draining review is also the cheapest parallel work available, because it is mostly
read-and-decide rather than build. Suggested split: one worktree per area
(`ui` 37, `gameplay` 31, `graph` 18, `world` 15, `items` 13, `triggers` 13), each
verifying against the same gate.

**Recommended order: drain review first, then re-cut the todo lanes.** Reviewing may
delete or shrink work in the queue, and it removes hub contention before the arms start.

---

## 5. Rules of engagement

1. **Never `git stash`.** Stashes are shared across worktrees. For conflicts, rebase or
   merge the base branch into the worktree, resolve there, then merge or Apply.
2. **One owner per hub file.** Only WT-0 edits the eight hubs. Another lane that needs a
   hub change either does it behind a small PR or files it — never silently.
3. **Append-only files are shared.** `templates/index.html` and `tools/unit/run.cjs` may
   be appended to by any lane. Rebase before merging anyway.
4. **Every lane clears the same gate before proposing a merge:**
   ```
   python -m pytest -q                      # compare to the ~60 failed / 3239 passed baseline
   node tools/unit/run.cjs
   npm run lint
   npm run typecheck
   python tools/js_module_index.py --check  # or --write
   ```
   A new JS module also needs its `@module`/`@contributes` header and a script tag in
   `templates/index.html`.
5. **Merge order:** arms (WT-A, WT-B, WT-C) merge first and one at a time; the spine
   merges last, rebase-and-resolve inside its own worktree.
6. **Move task files as you go** — `python tools/tasks.py move --id N --status inprogress`
   then `--status review`, so two lanes never both claim the same task.

---

## 6. How many worktrees, honestly

| Lanes | Cross-lane merge conflicts | Verdict |
|---|---|---|
| 1 | 0 | everything serial, no gain |
| 2 | 263 | barely better than serial |
| 3 | 345 | marginal |
| **4 (1 spine + 3 arms)** | **385** | **recommended** — the arms are conflict-free, the collisions sit inside the spine, which is serial anyway |
| 6 | 425 | the extra lanes add nothing but merge debt |
| 8 | 442 | actively harmful |

Going past 4 does not help. The 57 conflict-free tasks cannot absorb more lanes than
there are areas, and the 52 hub-touching tasks are serialised by their own dependency
chain no matter how they are split.

**Realistic gain:** 3 arms × ~6–10 tasks each, running against a serial spine. If the
spine is the critical path, the throughput ceiling is set by how fast 397→398→400→401→402
lands — not by how many arms are running.

---

## 7. What not to parallelise

- **The world-scale chain (397→398→400→401→402).** Strictly ordered; splitting it
  guarantees conflict churn.
- **Anything touching `engine/tick_manager.py` or `engine/serialization.py`.** 23 queued
  tasks between them. These are the merge-magnet files.
- **Review tasks that claim a hub**, until the todo lane that owns that hub has merged.
- **The `area-major tick iteration` subtree (416→418, 416→419).** Same reason.

---

## 8. First five steps

1. Commit the pending Eldenford work on `master` so worktrees fork from a current base.
2. Write `.kilo/setup-script.ps1` (`npm install`, and any Python env note) and
   `.kilo/run-script.ps1` (start the app on a port derived from `WORKTREE_PATH`).
3. **`python tools/tasks.py validate` currently errors**, so a lane cannot address a task
   by id unambiguously. `bug-54` is used by two different files:
   - `todo/bugs/bug-54-weather-is-invisible-to-the-engine-…md`
   - `todo/testing/bug-54-test-social-company-passes-alone-…md`

   Renumber the newer one (the test-isolation bug, filed 2026-09-27) and fix any
   cross-references. There are also ~12 advisory `frontmatter status != folder` warnings
   and ~12 non-conforming filenames; the folder is authoritative so those are cosmetic,
   but the duplicate id is a hard error.
4. Drain the 21 review tasks with no file footprint — a free afternoon, zero conflict.
5. Cut the three arm worktrees from the task lists in §3, spine included, and let the
   arms run while the spine grinds through task-397.

---

## Appendix — how the file footprints were derived

`docs/virtualWorld/dev_tasks/{todo,inprogress,review}/<area>/<kind>-<id>-<slug>.md`
was parsed for every file path mentioned in prose, in fenced code, and in frontmatter.
Bare filenames (`world_compile.py`, `item-library.js`) were resolved against an index of
every tracked file in the repo, preferring `engine/`, `routes/`, `static/js/`, `tests/`,
`tools/`. Directory mentions were kept as single tokens so two tasks editing different
files in the same library directory still register as related.

**This is an approximation.** A task's *survey* section names files it only reads, so
some footprints overstate what will be edited. The lane boundaries are therefore
deliberately conservative — anything touching a hub went to the spine regardless. Before
a lane starts, its lead should confirm its file list from the task's Acceptance section
and say so on the board if a task turns out to need a hub it was not assigned.
