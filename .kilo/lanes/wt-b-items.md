# WT-B — Items and inventory

**Parallel arm.** You touch no hub file. Merge first.

## Your queue — 9 tasks

| Task | Priority | Title |
|---|---|---|
| task-513 | high | Kraktooth goblin gear spec-driven library batch |
| task-504 | medium | Item quantity property and pooled resource nodes |
| task-493 | medium | Item part/component model for devices |
| task-515 | medium | Item ownership and personal-item permission |
| task-516 | medium | Concealed carried items for hidden pouches and backup knives |
| task-517 | medium | Carried recreation and performance items |
| task-518 | medium | Ranged weapons and ammunition |
| task-332 | medium | Migrate legacy item effect props to triggers, then remove support |
| task-454 | medium | Save list must not parse every save file on each modal open |

Suggested order: **task-504 first** — it gates WT-A's task-569. Then 493 (the part/component
contract that 516 and 518 build on), then the content batches 513 / 515 / 517, then 516,
518, 332, 454.

## Primary files

```
engine/equipment.py       engine/items/       engine/toggleable_items.py
engine/crafting.py        engine/item_actions.py
data/library/items/       tests/test_item_quantity.py
```

## Cross-lane

- **task-504 blocks task-569** (WT-A, biome resource distribution). Ship it early and say
  so on the board.
- **task-493 is referenced by task-492** (docs, WT-0) — the item/action reference page
  documents the part/component contract. Land 493 before 492 does its final pass.

## Notes on specific tasks

- **task-332** is a data migration across ~461 items in 15 scenario files, not a code
  change. Do it as its own commit so it can be reverted cleanly. The task file has the
  full per-file breakdown.
- **task-454** touches save-file listing, which is close to `engine/serialization.py`
  territory. If you find yourself needing that file, it is a hub — note it on the board
  for WT-0 instead of editing it.

## Rules

- Full rules in `.kilo/lanes/README.md`.
- Do not edit any of the eight hub files.
- `templates/index.html` and `tools/unit/run.cjs` are shared append-only.
