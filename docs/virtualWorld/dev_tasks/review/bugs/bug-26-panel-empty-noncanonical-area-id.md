# Bug 26 — Human turn panel empty for areas whose id isn't the canonical form

**Status:** In Review — fixed 2026-08-24, name-based resolution +
getter validation, 1 new test, full suite 1126 passed. Browser E2E
pending (Tommy's men's restroom is the live repro).

## Found

2026-08-24 playtest: jake in "Taco Bell Men's Restroom" — panel showed
nobody / nothing of note / no ways out, and no area description under the
chip. Changing the light level (it was pitch black) changed nothing —
darkness only degrades chip labels, never empties them. The dining room
(no apostrophe) rendered fine.

## Why

`scene_snapshot._area_node_id` resolves via a getter chain that returns
CONSTRUCTED ids: `NodeIDHelper.area_node_id("Taco Bell Men's Restroom")`
→ `area_taco_bell_men's_restroom` (apostrophe kept). The hand-authored
node is `area_taco_bell_mens_restroom` (apostrophe stripped). The id
resolved to NO node → area_node None (no description) → all three graph
walks (people/items/ways) queried a nonexistent id → empty lists. The
YOU strip still worked because vitals come from the player object.
The agent path never breaks on this: `area_description` resolves areas
by iterating nodes and matching NAME.

task-333 previously patched a 500 crash in this same chain; the silent
empty-result case survived it. Fourth drift incident — see task-341.

## Fix

`engine/scene_snapshot.py::_area_node_id`:
- each getter result is now VALIDATED (must resolve to an existing area
  node) before being accepted;
- a name-based node lookup (normalized: lowercase, apostrophes stripped)
  runs before the canonical-id fallback — same source of truth as
  area_description.

## Tests

`tests/test_scene_snapshot.py::test_noncanonical_area_id_resolves_by_name`
— area node at a non-canonical id with an apostrophe name; asserts the
scene resolves the right area id, renders the description, and lists the
item and way.

## Verification

- pytest full suite 1126 passed
- Browser: reload jake's turn in the men's restroom — toilet chip, "out"
  way, and the area description must all render.
