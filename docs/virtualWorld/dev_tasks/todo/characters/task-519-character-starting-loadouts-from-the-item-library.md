---
type: task
status: todo
area: characters
priority: high
---

# task-519: Character starting loadouts from the item library

**Filed:** 2026-09-24
**Related:** task-17, task-55, task-408, task-450

## Goal

Make character `inventory` entries that reference library ids materialize
losslessly and support equipping, then wire the six goblins' starting gear from
the task-513 templates.

## Context (measured in `routes/library_ops.py`)

Character library entries carry `inventory` and `equipped`
(`data/library/characters/Gribba.json:68,71`; the six goblins are empty). On
import (lines 540-579):

- A **string** inventory entry (a library id) copies only `description,
  actions, uses, weight, tags, current_state, library_id, image` (lines
  551-560). It **drops `equip_slots`, `damage`, `damage_type`, `defense`,
  `insulation`, `light_level`, `triggers` and `contents`** — a library weapon or
  armor loses its stats and triggers.
- A **dict** entry uses inline `properties` as-is (a flattened copy,
  `library_id` optional) — full props are possible but it is not a template
  link.
- `equipped` is assigned from `cdata` (lines 513-515) *before* inventory
  materializes (line 540), so it cannot refer to a just-loaded library item.
  Existing equipped keys look like `item_<name>` (`elena vance.json:102-108`)
  while loaded inventory nodes are named `item_<player>_<name>` (line 550),
  which is a mismatch risk (see task-450 for the carried+equipped invariant).

Richer helpers already exist: `materialize_library_item` and
`_spawn_library_item_node` (`routes/library_ops.py:110-194`) preserve library
props and recurse `contents`; the `give_item` effect
(`engine/effect_handlers/spawn.py:141`) places a library item into inventory.
task-17 (done) already pre-fills starting gear via the paperdoll editor; task-55
auto-adds new items to the library.

## Proposal

- Route the string-library path (and ideally the dict path) through the existing
  materializer so a referenced template lands with its stats, `equip_slots`,
  triggers and `contents` intact.
- Define the canonical loadout representation: library id references
  (preferred), with instance `properties` only for per-character overrides.
- Materialize inventory before resolving `equipped`, and let `equipped` name a
  library item/slot so a starting loadout can be worn, not only carried.
- Then author the six goblins' loadouts from the task-513 templates (weapons,
  armor, tools, accessories), consistent with the gear matrix.

## Acceptance

- `inventory: ["<lib_id>"]` on a library character produces an item node that
  preserves `equip_slots`, `damage`/`damage_type`, `defense`, `insulation`,
  `light_level`, `triggers` and `contents` (tested).
- An `equipped` entry can assign a library item to a valid slot on load, and the
  carried+equipped invariant holds (task-450).
- The six goblins load with their starting gear and no duplicate/orphan items.
- Scenario/library validation stays clean.

## Non-goals

- Runtime save-format changes beyond loadouts.
- Reworking the equipment slot set (task-513 covers partial-armor mapping).

## Verification

- Route/library test asserting preserved properties for a string reference.
- A load test for a goblin with weapon and armor equipped.
- `python -m pytest tests/ -q` for saveload/library/character tests.
