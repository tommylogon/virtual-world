# Scenario Generator — first-pass procedural assembly from area pieces

`tools/generate_scenario.py` — assembles a playable scenario from library area
pieces. This is a **first pass**, deliberately small and deterministic.

## Confirmed capability: area pieces already carry item copies

- `data/library/areas/*.json` support an `items` array. **51 of 90 areas have a
  non-empty `items[]`** (217 embedded item definitions total, all inline dicts).
- Runtime support already exists:
  - `routes/library_ops.py:handle_library_import_area` (line 537) materializes an
    area's `items` as item nodes with `in` edges, recursing into `contents`.
  - Route: `POST /api/library/areas/<id>/import`.
  - Area duplication clones items/contents/triggers
    (`tests/test_duplicate.py::test_duplicate_area_clones_items_contents_and_triggers`).
- Goblin camp pieces with items: `camp_entrance_trail` (4), `cooking_area` (3),
  `goblin_nursery` (7), `healing_area` (2), `scouting_rooms` (1), `training_pit` (5),
  `workshop` (2). Many camp areas still have `items: []`.

So the pipeline gap was never "areas can't hold items" — it was that the
scenario assemblers ignored the area `items` arrays and hand-placed items.

## Pipeline

```
pieces (data/library/areas/*.json)
  → select   (tag filter + exit-hint BFS from a root + seeded fill)
  → emit     (area nodes, item copies with `in` edges, ways from exit hints)
  → validate (tools/validate_scenario.py)
  → write    (data/scenarios/<name>.json)
```

## Usage

```bash
# Thematic subset by tag
python tools/generate_scenario.py \
    --name kraktooth_generated --tags goblin_camp --root camp_entrance \
    --seed 7 --max-areas 30

# Connected group via exit hints (no tag filter; includes untagged camp areas)
python tools/generate_scenario.py \
    --name kraktooth_generated_connected --root camp_entrance_trail \
    --seed 7 --max-areas 25

# Flags: --no-items, --disconnected, --player, --library, --output
```

## What it does

- **Selection** — filters pieces by `--tags`, then walks `exits[].target_room_hint`
  from `--root` (or the most-connected piece) so the result is contiguous; seeded
  random-fill tops up to `--max-areas`. Pool order is sorted + `random.Random(seed)`.
- **Item copies** — each embedded item dict becomes an `item_<area>_<name>` node
  with an `in` edge to its area; nested `contents` recurse. Weapon/armor/container
  tags get sensible defaults (damage, equip_slots, capacity).
- **Ways** — every exit whose hint resolves to another selected area becomes a way
  node with four `connection` edges; unordered pairs are de-duplicated. Boundary
  exits that leave the selection are reported as unresolved (not invented).
- **Runtime** — one player at the root area. `current_area` is the area **display
  name** (engine convention — see gotcha below).
- **Determinism** — same seed + same library + same flags → byte-identical output
  (verified via SHA256).

## Verified output

```
Seed 7 | tags=all | areas=25
Nodes: 25 areas, 27 items, 25 ways | edges=127
Validation passed.
```

Loaded live: `POST /api/load` → success; `GET /api/scene/player_explorer` →
`name=Camp Entrance Trail`, `desc="A narrow forest trail..."`, `items=4`,
`ways=2` (Camp Entrance, Deep Forest), `people=0` duplicates.

## Engine conventions learned (and now enforced by the validator)

- `player.current_area` must be the area **display name**, not the node id —
  `engine/room_perception.py:resolve_area_node` matches by name first. Storing
  ids strands characters in phantom `area_area_*` areas.
- Do **not** author graph `character_*` nodes alongside `players`; the engine
  creates `player_<key>` anchors, so both produce duplicates. `pines.json` uses
  one `player_<key>` node per key and no `character_*` nodes.
- `tools/validate_scenario.py` now accepts area **names or ids** for
  `current_area` / `area_from` / `area_to`, matching runtime behaviour.

## Known gaps (intentional for a first pass)

- Empty areas are furnished only when `--populate` is passed (see below); the
  default path uses the piece's own `items[]`.
- No trigger materialization from piece `triggers`.
- No characters, lore, or schedules beyond one player.
- Boundary exits are reported, not auto-wired to outside pieces.
- No recipe/lock-file provenance beyond the `_generation` block.

## Procedural population (`--populate`, task-9)

`engine/population.py` furnishes areas by walking one domain tag down a chain:

```
area domain tags
  -> furniture with a role tag (display / container / storage) and a matching domain
  -> items with a matching domain
```

Matching is set intersection; planning is pure and deterministic. No silent
substitution — a domain with no library candidates is reported in
`unresolved_domains` and the area is left unfurnished.

```bash
python tools/generate_scenario.py --name kraktooth_populated \
    --root camp_entrance_trail --seed 7 --max-areas 20 \
    --populate --items-per-area 6
```

Placement relations: `in` for container/storage furniture, `on` for display
furniture, `at` for loose floor items. `apply_population(plan, spawn, relate,
area_node_id)` takes caller callbacks so the engine never depends on Flask.

### Domain tagging pass (`tools/tag_domains.py`, task-324)

Adds the shared domain tags the chain needs. Dry-run by default.

```bash
python tools/tag_domains.py           # report
python tools/tag_domains.py --apply   # write
```

Scoped to the goblin camp in this pass: 22 areas, 27 furniture items, 27 items;
tag library 521 → 535.

## Related dev tasks

| Task | Status | Relation |
|---|---|---|
| **task-357** structure save/load (connected-area bundles) | todo | Closest sibling: save a connected area group (with items) as a named bundle and re-import. |
| **task-381** room-template palette | review | Authoring UI for "New Room from Template". |
| **task-364** scenario-from-text wizard | review (implemented) | LLM drafts a whole scenario; this generator is the deterministic counterpart. |
| **task-9** tag-chain item population | **implemented here (v1)** | `engine/population.py` — engine + tests; route/editor integration still open. |
| **task-324** domain tag schema + area tagging | **partial (goblin camp)** | `tools/tag_domains.py`; 35 non-goblin areas still untagged. |
| **task-398** deterministic structure generation | todo | Recipes + `GenerationPatch` — this generator + population is a working precursor. |
| **task-289/290/317** template link sync / variants | todo | Keeping pieces in sync with placed instances. |
| **task-404** character life-experience generator | todo | Character-side procedural content. |

## Population status (this pass)

- `engine/population.py`: `LibraryIndex`, `plan_population`, `apply_population`.
- `tests/test_population.py`: 7 tests (determinism, role selection, cross-domain
  exclusion, unresolved reporting, callback application).
- Goblin camp result: 13/20 selected areas furnished; unresolved domains
  reported honestly (e.g. wilderness `forest`/`wild` has no interior content set).
- `tools/lint_library.py`: `area_tag_gaps` 38 → 35 (goblin areas covered; the
  remaining 35 are mansion/pines areas outside this pass).

