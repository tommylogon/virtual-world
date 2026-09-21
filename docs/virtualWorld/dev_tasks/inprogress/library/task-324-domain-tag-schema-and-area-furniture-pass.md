---
group: Library
---
# Domain Tag Schema + Area/Furniture Tagging Pass

## State (verified 2026-09-21) — partial, not closable

**Landed:** the nine missing tag files under `data/library/tags/` with the schema
this task specifies (`store.json:5,21-23`, `display.json:5`,
`clothing.json:1-26` matching the task's own example verbatim); the
`tools/tag_domains.py` script (dry-run by default, `:201-205`); the `display` role
tag applied across the furniture items (`shelves.json:15`, `table.json:15`,
`desk.json:17`, `bookshelf_item.json:16`, `fireplace.json:18`, and others); and a
**goblin-camp** area-domain pass (`tools/tag_domains.py:52-75`, e.g.
`data/library/areas/shaman_lair.json:8-10` getting `shrine`, `occult`).

**Not done — this is the bulk of the task:**
- **The area domain backfill is a goblin-camp pass, not the all-areas pass this
  task requires** (`:121-123`). ~33 area files still carry an empty top-level
  `tags: []`, including the ones the task names explicitly — the literal `library`
  and `kitchen` areas (`data/library/areas/library.json:4`, `kitchen.json:140`) —
  plus `pantry`, `cellar`, `study`, `wine_cellar`, `conservatory`, `crypt`,
  `graveyard`, `dining_area`, `living_room`, `master_bedroom` and others.
- **The verification targets are unmet:** "60/60 areas have tags" and
  "509 + 9 = 518 registered tags" (`:130-134`). `tools/lint_library.py:125-131`
  (`area_tag_gaps`) would still warn on the untagged areas above.
- **The docs convention is absent:** step 4 (`:126`) asks for it in
  `docs/virtualWorld/Library System/`; there is no domain/role-tag convention doc.
- Minor: `tools/tag_domains.py:13` advertises `--domains goblin` but argparse only
  defines `--apply`.

**Not superseded** — downstream work depends on this and says so:
`docs/virtualWorld/dev_tasks/mujeeroth-scale-plan.md:22` lists task-324 as
unstarted, and `todo/world/task-400-...md:28-30` / `task-398-...md:90-92` state
the Pines areas "have no domain tags" and forbid assuming the backfill exists.

**Suggested next slice:** apply the domain table to the mansion/Pines area
library (the ~33 empty ones), extend `tools/tag_domains.py`'s table beyond the
goblin camp, then write the convention doc. The tag files and script already
exist, so this is a data pass plus documentation, not new machinery.

**Filed**: 2026-08-21  
**Priority**: Medium  
**Status**: Planned — blocked by task-323 (lint should validate the result)

---

## Summary

Establish the **domain tag convention** that powers task-9's population chain:
the *same* domain tag appears on areas, on display/storage furniture, and on
items — then a population pass is just set intersection down the chain.
Register new tags in `data/library/tags/`, backfill area tags (35/58 lack any),
and role-tag furniture (`display` vs `container`/`storage`).

## The Convention

```
Area  "Clothing Store"   tags: [store, clothing]
  └─ Rack                tags: [furniture, display, clothing]      → ON/BESIDE placement
  └─ Wardrobe            tags: [furniture, container, storage, clothing] → IN placement
       └─ Dress          tags: [clothing, outerwear]
```

Rules:

1. **Domain tags describe what a place is FOR** (`store`, `clothing`, `kitchen`,
   `library`, `occult`) — distinct from existing setting tags (`fantasy`,
   `school`, `modern`) which say what world it's in. Both can coexist on an area.
2. **Role tags on furniture**: `display` = surface placement target (racks,
   shelves, tables, mannequins); `container`/`storage` = containment targets.
   A piece may have both (dresser: `in` for drawers, `on` for top surface).
3. Every new tag gets a file in `data/library/tags/` with category/applies_to
   metadata (382 files already follow this; mechanical tags carry
   `category: "mechanical"`).

## Current State (survey 2026-09-08, verified)

- Areas: 25/60 have tags; 35 lack any tags. See appendix for full list.
- Items: 47 items carry `furniture` tag; 22 of those also have `container`.
  **No `display` tag exists anywhere.** No furniture has role+domain tags
  beyond incidental ones (e.g. `restaurant`, `bathroom`, `outdoor`).
- Tag library: 509 registered tags. **None of these exist as files**:
  `store`, `kitchen`, `display`, `clothing`, `library`, `occult`.
  (`furniture`, `container`, `storage` are used as tags on items but have
  no dedicated tag metadata files — add them for consistency.)

## Survey Output (2026-09-08)

```
Total tags: 509
store exists: False
kitchen exists: False
display exists: False
clothing exists: False
furniture exists: False
container exists: False
storage exists: False
library exists: False
occult exists: False
Areas WITH tags: 25
Areas WITHOUT tags: 35
Furniture items: 47
```

## Tag Schema (2026-09-17)

All 509 existing tags remain valid. New tags extend the schema with two
optional arrays while keeping every legacy field unchanged.

```json
{
  "name": "clothing",
  "description": "Apparel and wearable fabric items.",
  "category": "concept",
  "contexts": ["shop", "residential", "loot", "dungeon"],
  "implies": [],
  "applies_to": ["area", "item"],
  "color": "#9b59b6",
  "icon": "👕",
  "examples": ["shirt", "dress", "cloak", "boots"]
}
```

**Fields**
- `category` — what it IS: `domain`, `concept`, `role`, `setting`, `material`, `environment`, `custom`
- `contexts` — where/how it applies: `shop`, `residential`, `industrial`, `dungeon`, `outdoor`, `loot`, `generic`, `placement`
- `implies` — auto-decomposition: `potion_shop` → `["potion", "shop"]`
- Legacy fields unchanged: `applies_to`, `color`, `icon`, `examples`, `description`

**Query axes for population**
1. `category=concept AND context=shop` → shop-appropriate items
2. `category=domain AND context=dungeon` → dungeon area domains
3. `implies contains X` → anything that decomposes to X

**No prefix namespace needed.** A single tag file carries all dimensions;
the population layer filters by `category` + `context` instead of
inventing `domain_clothing` / `concept_clothing` / `loot_clothing`.

## Appended Work Plan

Add step 0 before the existing steps:

0. **Create the missing tag files** in `data/library/tags/` using the schema
   above:
   ```
   store.json, kitchen.json, display.json, clothing.json,
   library.json, occult.json, furniture.json, container.json, storage.json
   ```

## Updated Work Plan (numbered)

0. Create the 9 missing tag files above.
1. Derive domain tags from the 35 untagged area files — do not invent domains
   that nothing uses. Minimum domains needed: `store`, `kitchen`, `library`,
   `occult`, `clothing` (from scenario areas in `data/scenarios/pines.json`).
2. Script `tools/tag_domains.py` (dry-run default):
   - Per-area domain table for all 60 library areas
   - Per-furniture role+domain table for the 47 furniture items
   - Validates every tag against `data/library/tags/` + item vocabulary
3. Apply, then run task-323 lint — checks 3/4 must stay clean
4. Document the convention in `docs/virtualWorld/Library System/`

## Verification

- `python tools/lint_library.py` → 0 errors, area coverage warning gone
- Spot-check: a `clothing`-tagged area + `display` rack + clothing items form
  a connected chain (the exact query task-9 will run)
- Tag count: 509 + 9 = 518 registered tags
- Area coverage: 60/60 areas have tags

## Dependencies

- Blocked by: task-323 (lint validates this pass's output)
- Blocks: task-9 implementation (chain needs real domain tags to walk)

