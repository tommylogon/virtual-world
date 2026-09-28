---
type: task
status: review
area: world
priority: medium
---

# task-565: Migrate the goblin camp scope id off deep_woods_2

**Filed:** 2026-09-27
**Related:** task-560 task-496

## Goal

The scope's display name is already 'goblin camp'; the id is still deep_woods_2 because ids are minted once as a slug of the name at creation (routes/world_grid_ops.py:237) and the rename route only touches the display name. The project's rule is that ids change and display names do not, so the id is what is stale. Migrate deep_woods_2 -> goblin_camp: the world_scopes key, world_scope_id on all its areas, the parent's placements key, then regenerate the zone so area_deep_woods_2_x_y node ids follow. Check the OUTER deep_woods scope first - if it is genuinely a forest zone wrapping the camp, its id and name are correct as they are and only the interior changes. Scope ids are immutable by design, so this needs a one-off migration script, not a route.

## Acceptance

- The goblin camp scope's id is `goblin_camp`, matching its display name.
- No reference to `deep_oods_2` survives anywhere in the scenario.
- The scope tree is still coherent: every `parent_id` matches a `children` entry
  and vice versa, and every `area_ids` entry names a node that exists.
- The outer `deep_oods` scope is untouched.

## Progress — 2026-09-28 (in `review`)

`tools/migrate_scope_id.py` (new, idempotent, dry-run by default). Applied:
**24 references renamed, 0 leftovers.** `deep_oods_2` no longer appears in
`data/scenarios/kraktooth_goblin_camp.json` at all.

### The task's last step was moot, and worth saying so

The task said "then regenerate the zone so `area_deep_oods_2_x_y` node ids
follow". **There are no `area_deep_oods_2_*` node ids** — measured 0. The camp's
21 areas are hand-authored (`area_chiefs_pit`, `area_camp_entrance`,
`area_water_source`, …), not grid-compiled, so there is nothing to regenerate. The
migration is a pure rename of the scope record and its referrers.

The mechanism is implemented and tested anyway (`test_the_migration_renames_area_ids_minted_from_the_scope_id`),
because the `west_oods` scope's 53 areas *are* grid-compiled and
`area_west_oods_10_14`-style ids are exactly what a future rename there would have
to follow. Doing it now, on the shape the compiler actually emits, is cheaper than
discovering it during the next rename.

### The outer `deep_oods` scope: checked first, and left alone

The task asks to check it, and it is genuinely a forest zone: a painted 45×30
grid, no areas, no children, and its id and name already agree (`deep_oods` /
"deep woods"). Its id is not the stale one. Renaming it would churn a scope
nobody asked about. A test pins all of that so a later "while we're here" does not
quietly do it.

### Two bugs this task's own tests caught, both in the migration

Both are the failure mode the task warns about — *"a silent half-rename is worse
than a stale one"* — and both looked healthy:

1. **A node's `id` was renamed but not the dict key it sits under.** The graph
   ended up with `nodes["area_deep_oods_2_10_14"]` holding a record whose `id` was
   `area_goblin_camp_10_14`. Every reference to that node dangles and nothing looks
   wrong. Both now follow, and a **node-id collision aborts the migration** rather
   than silently dropping a node.
2. **`area_ids` on the scope still named the old node id.** A scope whose list
   points at a node that is no longer there is fine until load, which is the worst
   place to find out. `area_ids` across every scope now follows the rekey.

### The leftover scan is the safety net, and it is a substring search

After the rename the whole document is walked for any surviving mention of the old
id — as **substring**, not equality, because a reference in a shape the script did
not anticipate is exactly what a substring catches and an equality check would
miss. Leftovers are **reported and the write is withheld**, so a half-understood
schema is a report rather than a broken save.
`test_the_migration_reports_an_unrecognised_reference_instead_of_ignoring_it` pins
this with a `some_future_field` the script knows nothing about.

Re-running is a *success*, not an error: it says `already migrated`. A re-run is
the normal way to confirm a migration took, and an error there would teach people
to ignore the output.

### New tests — `tests/test_scope_id_migration.py` (16)

The camp after: id matches name, no surviving reference anywhere (substring scan
over the whole document), the outer scope untouched, **the tree still coherent**
(every `parent_id` has a matching `children` entry and vice versa, no dangling
parent), the camp still owning its 21 areas with `area_ids` and the nodes agreeing,
the child scope repointed and no other scope moved.

The migration: every reference renamed; cell areas minted from the scope id
following both key and record; a no-op second run; refusing to merge two scopes;
leaving the input untouched on a refusal; refusing a scenario with no scopes;
saying so when there is nothing to rename; and the leftover report.

### Note for whoever picks up task-565's follow-on

The camp's **104 ways carry no `world_scope_id` at all** (`None`), while every area
carries one. So a scope-level query over ways returns nothing. That is a WorldPainter
compiler gap rather than a migration gap, so it is not fixed here, but it is the
same class of problem this task is about: an area knows which scope claims it and a
way beside it does not.
