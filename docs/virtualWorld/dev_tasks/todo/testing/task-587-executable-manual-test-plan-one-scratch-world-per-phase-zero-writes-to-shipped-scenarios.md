---
type: task
status: todo
area: testing
priority: high
supersedes: test-plan-100-items.md
related: [task-586, task-444, task-572, task-574, bug-54]
---

# task-587: Executable manual test plan — one scratch world per phase, zero writes to shipped scenarios

**Filed:** 2026-09-29
**Related:** task-586, task-444, task-572, task-574, bug-54
**Supersedes:** `docs/virtualWorld/dev_tasks/done/testing/test-plan-100-items.md`

## Overlaps task-574 — do not write the same steps twice

`task-574` (inprogress) is a per-feature test guide for everything built on 2026-09-27, in exactly the right shape already: **what it is / how to test it by hand / what passing looks like / the automated coverage that already guards it**. That is the per-feature content. This task supplies what a guide cannot: the world each step runs in, what it may write, and the gate. So phase 9 (painted world) should link to task-574's entries rather than restate them, and the WorldPainter steps should move under this task's phase structure rather than being duplicated.

## Goal

The 215-step click list in `done/testing/test-plan-100-items.md` is a presence check, not a plan: it has no world per step, no write-safety, and no contamination gate, so every step silently runs against the booted default world and is allowed to write to it. Restructure it so each phase runs in its own scratch scenario, each step declares what it may write, and a git-clean gate voids the run if anything touched a shipped file.

## There is already a checklist — do not write a second one

`done/testing/test-plan-100-items.md`: 20 sections, **215 numbered steps**, method "Playwright headless against `http://127.0.0.1:4444`". Problems, in order of severity:

- **It has never been run to a result.** The status column is `✅ / ❌ / ~` and every cell is empty; the glyphs are also mojibake (`âœ“`), so the file is both unmaintained and broken UTF-8.
- **It is filed under `done/`.** A 215-step plan with no results is not done.
- **It has no world model.** No step says which world it runs in or what it may write. Every step implicitly runs on whatever the server booted — the root `world_template.json` — and is permitted to write to it.
- **It predates the newer subsystems.** No coverage of WorldPainter/compiled regions, scopes, the staging batch path, the changes panel (`GET /api/scenario/diff` -> apply/discard), tags, population, timeskip, world lore, or the background simulation. bug-54's missing open-sky tag on compiled areas is exactly the class of defect a "load a painted world and look at the light" step would catch, and no such step exists.

The Playwright side is not missing either: `tools/test_helpers.cjs` plus 28 `.cjs` harnesses already drive a live server, and **task-444** tracks finishing them. This task is about the *plan* they and a human share.

## Why "edit a scenario and revert it" cannot be the model

Not a style preference — four concrete failures:

1. **No lock, and there is a second writer.** Autosave runs on turn (`routes/helpers.py`), `POST /api/save-game` writes from the same world (`tools/test_all.cjs:227`), and the editor writes node images. A `git checkout` revert races all three, and the result is a corrupted shipped scenario rather than a reverted one.
2. **A booted world is designed to write itself back.** `POST /api/scenario/commit` writes to `_scenario_source`, which after a normal boot is the root `world_template.json` (`app.py:62`). "Test on the template, revert after" is one stray keystroke from destroying the file, and the test cannot report that it happened.
3. **A failure needs the state as of that step, not twelve steps later.** One world reused across a phase means every rerun starts from a different place, so "it failed" is not reproducible.
4. **Contamination reads as an application bug.** bug-55 is the worked example: a full turn let the cast wander into the room under test, and the resulting order-dependent failures were filed as a `create_app()` isolation defect. A plan that reuses a mutable world will keep manufacturing that class of false positive.

## The model that replaces it

**One scratch world per phase, created fresh, never reused across phases, never a shipped file.** Each step declares six fields so a human and a Playwright script can execute the same line:

| Field | Example |
|---|---|
| `id` | `2.7` — stable, referenced by the `.cjs` harnesses |
| `pre` | which world: `scratch` (fresh this phase) / `continue` (previous step's world) |
| `action` | one user-visible action, or one API call |
| `expect` | the observable that must be true — an assertion, not "it looks right" |
| `may-write` | `nothing` / `scratch-only` / `scratch+assets` |
| `evidence` | the log line, screenshot or JSON path that proves it |

Phases, each starting a new scratch world:

| Phase | Subject | Note |
|---|---|---|
| 0 | Boot & shell | server starts, no console errors, tabs present, **no file written by boot alone** |
| 1 | Empty scenario | **no such route exists today** — see below |
| 2 | Graph editor: empty -> one area | add, tag, light, save, reload, persisted |
| 3 | Two areas + a way | assert the *documented* id rule, not a guess: areas hard-error on duplicate id, items/ways/characters get suffixed (`graph.py:167-172`) |
| 4 | Items | library item into an area, takeable vs not per its declared actions, container, `uses` charge |
| 5 | Characters | add from the editor skeleton, traits, identity — and resolve the orphan `data/graph_editor_character_template.json` (nothing in `routes/`, `templates/`, `static/` or `tools/` references it by name) |
| 6 | Triggers | create, fire on a turn, and one undo snapshot per `POST /api/graph/batch` (`static/js/staging.js:177-193` claims atomic + strict validation — assert it) |
| 7 | Play a turn | movement, vitals, log lines, export the log, `node tools/log_lint.cjs` on it |
| 8 | Persistence round-trip | save -> reload -> assert equality, including two same-named areas in different scopes (task-446) |
| 9 | Painted world | compile a WorldPainter world, load, check areas carry `world_scope_id` — and the open-sky/light behaviour bug-54 leaves open |
| 10 | Changes panel | `GET /api/scenario/diff` -> apply / discard, and that apply is a single commit |

## The gate (this is the part that makes the plan trustworthy)

After **every** phase, and at the end of the run:

1. `git status --porcelain` is empty except the scratch directory and its assets.
2. The scratch world was created under `data/saves/<run-id>/` (or a temp `DATA_DIR`), never under `data/scenarios/`.
3. The runner booted with `_scenario_source` unset, so a stray commit **fails loudly** instead of writing to `world_template.json`.

A phase that trips any of the three voids the run and names the step. This is the whole anti-contamination mechanism and it costs one shell command.

## Phase 1 is a finding, not a test

There is no "new empty scenario" route. `/api/scenarios` offers list / duplicate / rename / delete / get; `/api/scenario` offers `name`, `commit`, `append`, `diff`, `diff/apply`, `status`. Starting from nothing is not a supported journey — `app.py:52-59` falls back to a single `Area("Living Area")`. Either add the route or accept that phase 2 starts from `duplicate` of a hand-made empty file. Decide before writing step 1.1; the plan is wrong either way until it is.

## Acceptance

- [x] `docs/virtualWorld/testing/manual-test-plan.md` exists, with all 215 existing steps re-expressed in the six-field form and mapped to a phase, plus the missing phases 1, 9 and the newer subsystems.
- [x] The old file is removed or reduced to a pointer, and no 215-step plan sits in `done/` without results.
- [x] Every step has a `may-write` value, and no step writes outside its scratch world.
- [x] The gate is scripted (`tools/test_plan_gate.cjs`) and fails on a dirty `git status`.
- [x] The plan names its blind spots explicitly: what is **not** covered and why.
- [ ] A first run is recorded with real per-step results, and `git status` is clean afterwards. **Partial** — see Outcome.

## Outcome (2026-10-02)

**Delivered.** `docs/virtualWorld/testing/manual-test-plan.md` (325 lines, **224
steps**): all 215 old rows migrated to the six-field table form and grouped under
phases 0/2/3/4/5/6/7/8, plus hand-written phases 1 (the missing-route finding),
9 (painted world) and 10 (changes panel). The old file is reduced to a pointer
with `status: superseded`. `tools/test_plan_gate.cjs` validates that every step
declares `nothing` / `scratch-only` / `scratch+assets` **and** that
`git status --porcelain` is empty outside `data/saves/<run-id>/` and `evidence/`.

**Gate, proven both ways:**
- on the uncommitted tree: `plan gate: FAIL — 3 shipped file(s) changed outside
  the scratch world` … exit 1;
- after commit: `plan gate: OK` … exit 0.
- plan validation: `plan gate: 224 steps, every one declares a may-write value`.

**First run — partial, recorded honestly.** Boot on `VW_PORT=4470`; the
representative browser run (`node tools/test_runner.cjs --suite full`) was
**11/11 passed** covering representative steps from phases 0, 4, 5 and 8, and
`git status` was clean afterwards (the temporary save slot and autosave were
removed). Phases 1/2/3/6/7/9/10 have **not** been executed; the plan's "First
run" section records that as the state, not as passes. The remaining execution
is a runner keyed by step id (task-444's `test_runner.cjs` is the foundation).

**Blind spots**, named in the plan: `may-write` is inferred from a step's verbs
rather than measured; the migrated steps carry no results; there is no empty-
scenario route (phase 1 is a decision); and `--phase` browser execution does not
exist yet.

**Why this is not `done`:** the last acceptance line needs a full per-step run,
which is execution work on top of an intact plan and gate. The plan is complete
and executable; the run is not.

## Follow-ups

- **task-586** is the foundation: the scratch world and the fixture should share one loader, and `solo()`/`company()` should be the only way isolation is expressed.
- **task-444** implements the steps that need a browser; this task only has to make them addressable by step id.
- **`data/scenarios/world_template.json`** is a hand-made backup of the root template, byte-identical, and it sits in the directory the scenario picker and `soak_runner` scan. It should move somewhere the app does not list — but it is the user's backup, so that move is theirs to approve.
