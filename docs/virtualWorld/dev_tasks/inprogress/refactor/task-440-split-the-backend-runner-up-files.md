---
type: task
status: inprogress
area: refactor
priority: medium
---

# task-440: Split the backend runner-up files

**Filed:** 2026-09-21
**Supersedes:** task-314's backend scope (which was measured 2026-09-21 and is now closed)
**Related:** task-83 (code readability), task-218 (the module-per-concern shape this follows)

## What

Extract focused modules from the backend files that outgrew single-file ergonomics.
**One file per commit, no behaviour change** — extraction only, public imports and APIs
stable, suite green after each.

## Measured targets (2026-10-16 remeasure)

Remeasured 2026-10-16 (`engine/`, `routes/`, plus the two root runners). Δ vs the
2026-09-21 card figures where comparable. **New entrants** were absent from the
original list and now sit above several of the tracked targets.

| File | Lines | Δ / note | Suggested seam |
|------|------:|----------|----------------|
| `engine/world_compile.py` | 2724 | **NEW** — repo's largest Python module | compile phases / layer emitters / way-property writers — find real boundaries before cutting |
| `routes/graph_ops.py` | 2016 | +661 | second pass: node CRUD / edges / batch / import-export |
| `virtual_world_engine.py` | 1926 | **NEW** (root runner) | only if a clean phase or facade seam exists; do not churn for linecount |
| `routes/player_ops.py` | 1668 | **NEW** | split by operation family (state / inventory / memory / update) |
| `engine/background_simulation.py` | 1668 | **NEW** | schedule / social / ambient ticks from the orchestrator |
| `routes/action_handlers.py` | 1632 | +331 | second pass: split by verb family |
| `routes/library_ops.py` | 1628 | +544 | second pass |
| `engine/tick_manager.py` | 1595 | +494 | extract tick phases (vitals / environment / triggers / activities) from the orchestrator |
| `player.py` | 1450 | **NEW** (root model) | only if a clean concern separates; Player already projects from node props — do not invent a second store |
| `engine/background_social.py` | 1389 | **NEW** | keep paired with `background_simulation` decisions |
| `engine/traits.py` | 1247 | +151 | definition catalog vs event dispatch |
| `engine/movement.py` | 1197 | +99 | traversal rules vs area/way construction |
| `engine/equipment.py` | 1144 | +390 | was lower priority; now above 1k — inventory/equip rules vs coverage/body |
| `engine/player_conditions.py` | 969 | +128 | was "tracked not to split"; re-evaluate if it keeps growing |
| `engine/serialization.py` | 940 | +431 | already imports `serialization_template` + `serialization_legacy`; prefer extending that split over a new cut |
| `engine/trigger_validator.py` | 930 | +109 | lower priority (also touched by task-393 family) |
| `engine/matching.py` | 924 | +227 | lower priority — resolve only if it keeps growing |

Also carried over from task-314's wave reports: `triggers/testing.py` (205) still
shares template-context shape with `triggers/execution.py` (629) — de-duplicate
while splitting if that seam is touched.

**Still not a linecount chase:** a cohesive ~900-line file may stay. New entrants
are listed because they outgrew the old list, not because every one must be cut
this wave. Prefer `world_compile.py`, `graph_ops.py`, and the `routes/*_ops.py`
family first — clearest operation-family seams.

## How

1. **One file at a time.** Start with the smallest target that has a clean seam, as the
   proof of pattern, then move up. Do not batch.
2. **No behaviour change.** Extraction only. Keep public imports/API stable, move public
   API re-exports up to the host module.
3. **Dedup & reuse pass (mandatory per extraction).** While splitting, scan the extracted
   concern and its host for duplicate logic, parallel data homes, and near-identical
   helpers; consolidate onto one owner instead of copying into the new module. Prefer
   reusing an existing seam (e.g. `serialization_template`/`serialization_legacy`) over
   creating a second one. Record any dedup decision in the move table.
4. **Agent-experience & cleanliness (mandatory per extraction).** Name modules by
   concern (not by size), keep each under ~600 lines where the seam allows, add a
   one-line module docstring stating its owner and its public surface, and ensure a fresh
   agent session can understand the module without reading the host. No new abstraction
   unless an existing seam already represents the concept.
5. **Record what moved** in the task file as a table (module → lines → what moved), the
   shape task-314's wave-1 table used.
6. Verify per extraction with a **targeted** selection (never the full suite by default;
   never `-q`): e.g. `python -m pytest tests/test_<touched>.py` plus any module that
   patches the moved symbol.

## Acceptance

- Each split lands with the host file's line count materially reduced and the package
  existing, verified by measuring both.
- No test file changes required beyond `mock.patch` targets that moved (record them).
- The suite stays green per extraction.

## Non-goals

- Behaviour changes, renames of public APIs, or architectural redesign.
- Chasing a line-count target — a file that is cohesive at 900 lines stays 900 lines.
- The frontend/JS and test splits (task-441).

## Why

Backend hosts above ~1.5k lines hold multiple operation families in one module, so callers and tests depend on an opaque file — and an agent session that touches one route family pulls the whole host into context. Remeasured 2026-10-16, the original 2026-09-21 list understates it: `world_compile.py` is 2,724 lines and was untracked; `routes/graph_ops.py` is 2,016 (+661); `virtual_world_engine.py` (1,926), `routes/player_ops.py` (1,668), `engine/background_simulation.py` (1,668), `routes/action_handlers.py` (1,632, +331), `routes/library_ops.py` (1,628, +544), `engine/tick_manager.py` (1,595, +494) are all new entrants. Prefer `world_compile.py`, `graph_ops.py` and the `routes/*_ops.py` family first — clearest operation-family seams. A cohesive ~900-line file may stay; this is not a linecount chase.

## Steps to verify

1. Remeasure host and new module after each one-file extraction.
   - expected: host line count materially lower; extracted concern has one owner;
     public import paths stable.
   - observed: 2026-10-16 remeasure recorded above; no extraction landed this pass.
2. Run the focused test module(s) that exercise the extracted behaviour (no `-q`).
    - expected: same behaviour passes; any changed `mock.patch` target is recorded.
    - observed: 2026-10-16 extraction #3 — `engine/serialization_helpers.py` (162 lines) from `engine/serialization.py` (965 → 836, −129). Moved the stateless payload helpers (`_body_region_catalog`, `_VITAL_KEY_ALIASES`, `canonical_vitals`, `_region_exposure_map`, `_goals_payload`, `_mosiac_payload`, `_trait_behavior`, `normalize_dials`, `_disposition_payload`) into the new module; `WorldSerializer` and the loader facade stay in `serialization.py`. Re-exported from `serialization.py` so `from engine.serialization import X` and internal bare-name call sites keep working; `TraitSystem`/`TRAIT_DEFINITIONS` import dropped from `serialization.py` (now imported lazily inside `_trait_behavior`). No `mock.patch` targets moved. `tests/test_disposition.py` + `tests/test_traits.py` 116/116 pass; `import app` clean.
3. Import the package and the extracted module in a clean process.
   - expected: no cycle / import-time side effect; stable public API still exposed.
   - observed: not applicable until an extraction lands.

## Files

- `engine/world_compile.py`, `tick_manager.py`, `movement.py`, `traits.py`, `equipment.py`, `background_simulation.py`, `background_social.py`, `matching.py`, `trigger_validator.py`, `serialization.py`, `player_conditions.py`
- `routes/graph_ops.py`, `player_ops.py`, `action_handlers.py`, `library_ops.py`
- `virtual_world_engine.py`, `player.py` (only if a clean seam is proven)
- new extracted modules under `engine/` / `routes/` as recorded per split

## Browser UI and intended live verification

Intended UI home: Not applicable — this is a one-file-at-a-time Python module extraction with an explicit no-behavior-change contract; no new browser surface is intended.

Current availability: the task requires smaller host modules while keeping public imports/APIs stable. The extraction sequence is not claimed as complete.

Why no browser UI: a screen interaction cannot establish that backend module boundaries changed without changing the public API or behavior; the proof belongs to imports, focused regression tests, and the measured source diff.

Alternative verification steps:
1. Before and after each extraction, record the host file's line count and inspect the new module's exported functions and imports.
   - expected: the host's line count is materially lower, the extracted concern has one owner, and public import paths remain stable.
2. Run the focused test module(s) that exercise the extracted behavior after each one-file split.
   - expected: the same behavior passes after extraction; any changed `mock.patch` target is recorded explicitly.
3. Import the application package and the extracted module in a clean process.
   - expected: imports have no cycle or import-time side effect and the package still exposes the stable public API.

This section is not a claim that planned UI exists or works today.


