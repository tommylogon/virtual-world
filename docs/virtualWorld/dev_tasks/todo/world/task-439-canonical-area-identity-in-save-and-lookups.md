---
type: task
status: todo
area: world
priority: high
---

# task-439: Canonical area identity in the save and in area lookups

**Filed:** 2026-09-21
**Blocks:** task-401 (chunk persistence — stable area ids, id-keyed `current_area`)
**Correction (2026-09-24):** this task no longer blocks **task-397**. The scope
layer shipped keying on node id / `world_scope_id` (`engine/world_scopes.py`,
`virtual_world_engine.py:138`) without requiring id-keyed saves, so 397 is
partial-and-unblocked. It also no longer blocks **task-438**, which was
cancelled in favour of the WorldPainter set (495/496/499/500); task-496's
compiler is expected to own ids. **task-401 is the real remaining dependent** —
the save layer is still display-name-keyed (`engine/serialization.py` writes
`rooms_serialized[node.name]`), and 401 needs `current_area` as an id.
**Related:** task-407 (graph edge indexing + case normalization), task-393 (validator triage), task-222 (serialize exits graph-only), `engine/serialization.py`, `docs/virtualWorld/World Building/Rooms & Areas.md`

## Goal

Make an area's **id** the canonical key everywhere it is persisted or looked up, so two
areas may share a display name without one silently overwriting, re-homing, or
mis-resolving the other.

This is the prerequisite for any world decomposition: splitting Deep Forest, Hills, Murk
Lake and the rest into sub-areas **guarantees** display-name reuse. `data/library/areas/`
already contains `weeping_willow_hollow`, `snowbound_hollow`, `frozen_hollow`,
`frozen_lake_clearing` and `blizzard_forest_clearing`; a decomposed world will have many
"hollows", "clearings" and "crossings" at once.

## Problem

The graph layer is already id-keyed and case-safe — `WorldGraph` resolves ids through
`_id_index` (`graph.py:70-77`), keys `self.nodes` by id (`graph.py:137-138`), and treats an
area **id** collision as a hard error while auto-suffixing items/ways/characters
(`graph.py:126-136`). The **save and lookup** layer is not:

1. **The save dict is keyed by display name.**
   `engine/serialization.py:191`:
   ```python
   rooms_serialized[node.name] = { ... }
   ```
   Two areas named "Hollow" collapse to one entry. This is silent data loss, not a
   performance problem — and it is the documented behaviour today
   (`docs/virtualWorld/World Building/Rooms & Areas.md:51-60`).

2. **Exits are resolved by display name.**
   `engine/serialization.py:197`:
   ```python
   "exits": self.player_manager.build_exits_for_area(node.name),
   ```
   Ambiguous once two areas share a name.

3. **`current_area` is compared by display name, first match wins.**
   `engine/serialization.py:77`:
   ```python
   if node.type == "area" and node.name == player.current_area:
   ```
   On a duplicate name this silently picks the wrong area, so a character can get the
   wrong area's temperature/environment. `Player.current_area` is a display-name string
   in 47+ references across 10 files
   (`docs/virtualWorld/dev_tasks/critical-review-scale-2026-09-08.md:48-57`).

4. **The save format carries two aliases for the same data.** `load_from_dict` reads both
   `areas` and `rooms` keys, so any change must touch both paths or they diverge
   (`critical-review-scale-2026-09-08.md:32-34`).

## Design

### Key by id, keep name as a field

- `rooms_serialized[node.id] = { "id": node.id, "name": node.name, ... }`.
- Apply the same change to every alias of the `areas`/`rooms` path in both
  `_serialize_world` and `load_from_dict`.
- `build_exits_for_area` takes the node id (or the node), not the display name.

### Ambiguity must be loud, not silent

Where a lookup genuinely only has a name (notably `Player.current_area`), resolution must
be **deterministic and reported**:

- resolve by id first when the stored value resolves to an area id
  (`graph._resolve_id`), otherwise by name;
- if a name matches more than one area, log a warning and pick by a stable rule
  (sorted id) **and** surface it in the validator — never silently take iteration order;
- de-duplicate on load as well as on save (a legacy save with colliding name keys has
  already lost data; do not compound it).

### Backward-compatible load

Legacy saves are name-keyed. On load, normalize name keys to ids. If two keys would
normalize onto the same id, or a name is ambiguous, record it in the load report rather
than dropping the entry silently.

### Interim authoring constraint

Until `current_area` is structurally id-based (see Non-goals), **display names must be
unique within a scenario**. Task-438's `split_area` therefore mints scenario-unique names
(e.g. "Deep Forest — Creek Margin") rather than bare "Creek Margin". This is also better
authoring practice.

### Validator rule

Add a duplicate-display-name diagnostic to the validator (task-393) and the library lint
(task-323): duplicate **ids** are already an error; duplicate **names** become legal at
the graph level but must be visible, so a scenario never ships with an ambiguity nobody
can see.

## Work plan

1. `engine/serialization.py`: key the serialized area map by `node.id` (include both `id`
   and `name` in the payload); update every `areas`/`rooms` alias path.
2. `build_exits_for_area`: resolve by id; update the `:197` call site.
3. `:77` temperature resolution: resolve by id, then unambiguous name; warn on ambiguity.
4. `load_from_dict`: normalize legacy name-keyed saves to id keys; produce a load report
   for collisions/ambiguities instead of silently collapsing.
5. Validator (task-393) + library lint (task-323): duplicate-display-name diagnostic.
6. Tests: round-trip a graph with two same-named areas in different regions and assert
   both survive save/load, both keep distinct exits, and each character's environment
   resolves to the correct area.

## Acceptance

- A graph containing two areas both named "Hollow" (ids `area_a_hollow`, `area_b_hollow`)
  round-trips through save/load with **both** present, distinct exits, and distinct
  environment/temperature resolution.
- Legacy name-keyed saves still load, with a report naming any entry that could not be
  normalized unambiguously.
- No regression: `python -m pytest tests/ -q -k "not mcp and not emote"`; add a
  serialization fixture covering the duplicate-name case.
- The validator flags a scenario holding two areas with the same display name.

## Non-goals

- **The `Player.current_area` string → id refactor.** That is 47+ references across 10
  files and is its own task (it gates task-401). This task only makes lookups
  unambiguous and loud, and its interim constraint is unique display names.
- Changing the graph node model — `WorldGraph` is already id-keyed; no change needed.
- Removing `exits` from the serialized area payload (that is task-222's question, tracked
  separately in `review/gameplay/task-222-serialize-exits-graph-only.md`).

## Risks

- **Legacy saves already lost data.** A save written while two areas shared a name cannot
  recover the overwritten entry; the load report can only surface that ambiguity existed.
- **`areas` *and* `rooms` aliases.** Touching one path and not the other makes the save
  and load disagree; assert both in the round-trip test.
- **Scope creep into the `current_area` refactor.** Keep the string-value change out of
  this task or it becomes unlandable; the interim constraint (unique names) is what makes
  the deferral safe.
