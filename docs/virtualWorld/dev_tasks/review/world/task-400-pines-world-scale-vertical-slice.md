---
type: task
status: review
area: world
priority: high
---

# task-400: Pines vertical slice for grouped generation and background life

**Filed:** 2026-09-08  
**Depends on:** task-397, task-398, task-399; task-323/task-324/task-9 for
tag-aware furnishing.

## Goal

Make `data/scenarios/pines.json` the first end-to-end proof of the scalable
world model. This is deliberately small: it proves semantics and authoring
workflow, not million-node performance.

## Scenario changes

1. Add a Millbrook Falls scope manifest with Downtown and The Pines hierarchy.
2. Assign existing Pines areas to their floor/building scopes.
3. Add an unmade `Apartment 3B` scope with recipe `apartment.v1` and a stable
   seed.
4. Add only the tag fixtures and library entries necessary for a credible
   residential apartment population test. Do not attempt a global library
   backfill in this scenario task. This is mandatory: the current Pines areas
   have no domain tags, so an untagged population demo would not validate the
   intended feature.
5. Add background schedules for five existing Pines characters, chosen for
   different outcomes: sleeping at home, working remotely, walking to work,
   consuming food/drink, and waiting/meeting.

## Demonstration script

1. Load Pines and open the Millbrook → Downtown → The Pines scope path.
2. Confirm the graph view returns only that projection; default UI does not
   reveal contained items.
3. Put five residents in background mode and advance eight hours.
4. Inspect their compact logs: location, activity, vitals, resource changes,
   and any deferred result.
5. Generate Apartment 3B from preview and walk from Hallway 3 into all its
   new areas.
6. Activate Miki; inspect her new `background` memory and full active prompt.
7. Save/reload; repeat scope navigation and prove no duplicate generated nodes
   or duplicate summary memories.

## Success criteria

The demo is successful only if generation, ordinary movement/item interaction,
background progression, and reactivation all use existing canonical data.
Hard-coded UI-only counts, narrative-only generated rooms, or direct mutation
that bypasses normal graph edges do not count.

## Explicitly not demonstrated

- Whole Millbrook generation.
- Multiple loaded chunks or disk eviction.
- Long road grids, fast travel, or cross-town route materialization.
- More than five background residents.

## Progress — 2026-09-24 (partial)

Authored slice (data only, via `tools/author_pines_slice.py`):

- **Scope manifest** in `data/scenarios/pines.json`: Millbrook Falls -> Downtown /
  The Pines -> Ground/Floor 1/Floor 2/Floor 3/Roof, with every existing area
  assigned a `world_scope_id` (a test asserts none is left unassigned).
- **Unmade `apartment_3b`** scope carrying `recipe: "apartment.v1"` and a stable
  seed — the generation hook task-398 will consume.
- **Five resident schedules** (miki, rose, kevin, haruka, mateo) with
  deliberately different days: working away, working at home, roaming, waiting,
  and a night routine.
- **task-399 proof**: offload/advance-eight-hours/promote on Miki yields one
  bounded `background` memory (see task-399). Tests: `tests/test_pines_slice.py`
  (7).

## Progress — 2026-09-28 (the generator is now actually reachable)

The 2026-09-24 note said the remaining work was blocked on task-398 because "the
generator they call does not exist yet". The generator existed; **nothing called
it**. `generation_recipes.get_recipe()` had exactly one caller — its own test —
while `POST /api/world/scopes/<id>/grid/generate` only ever ran the *grid*
compiler. An unmade scope that declared a recipe could therefore not be generated
at all, by any route, in any client. This is the third instance of the failure
mode now written up in `AGENTS.md`: a working mechanic, correctly tested, never
called.

- **Wired** (`routes/world_grid_ops.py`): a scope carrying a `recipe` generates
  through that recipe, via the same `apply_patch` contract the grid compiler
  uses. Seed comes from the body or the scope record and is required — a recipe
  with no seed is not reproducible, so it is a 400 rather than a surprise. The
  entry area is the scope's `entry_area_id`, else the parent scope's first area
  (the hallway a child apartment opens off).
- **Data**: `apartment_3b` now declares `"entry_area_id": "area_hallway_3"`
  explicitly rather than relying on the fallback.
- **Proved end to end** (`tests/test_pines_slice.py::TestGenerationEndToEnd`):
  - generating through the API produces the three areas and materialises the
    scope, with an empty `unresolved_tags` (asked-for tags the library could not
    satisfy stay visible rather than substituted);
  - **Miki walks in through the movement system** — `set_current_area`,
    `toggle_way("apartment door", "open")`, `move_to_area` — and reaches the
    living room and then the bedroom. The previous proof was structural only
    ("the way node exists"), which passed while the question of whether the door
    was actually enterable was untested;
  - a second generate is refused 409 and adds no node ids;
  - save/reload keeps every generated node and the `materialized` state, and a
    re-run after reload still refuses rather than doubling;
  - a hand edit is not erased by a refused second invocation.
- **Found and filed:** `allow_regenerate: True` *does* revert a hand edit, which
  contradicts task-398's acceptance — **task-585**.

### Still open

- **task-580** — the `Generate` button and the preview surface. The backend
  endpoint now works and nothing in the UI calls it, so demo step 5 ("from
  preview") is the only part of the script left, and it is a surface, not a
  mechanic.
- **task-585** — the `allow_regenerate` contract (see above).
