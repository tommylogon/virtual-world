---
group: Library
---
# Domain Tag Schema + Area/Furniture Tagging Pass

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

## Current State (survey 2026-08-21)

- Areas: 23/58 have tags, but values are setting-flavored (`bathroom`:
  `['fantasy','school']`) — no domain flavor anywhere yet
- Items: `furniture`(44), `container`(41), `storage`(6) exist; **no `display`
  tag**, no domain tags on furniture beyond incidental ones
- Tag library: 382 registered tags; `store`, `kitchen`, `display` need creating

## Work Plan

1. Register new tags in `data/library/tags/`: `display`, `store`, `kitchen`,
   `library`, plus any domains needed by scenario areas (walk the 58 area files
   and derive the list — don't invent domains nothing uses)
2. Script `tools/tag_domains.py` (dry-run default):
   - Explicit per-area domain table for all 58 library areas
   - Explicit per-furniture role/domain table for the 44 `furniture` items
     (rack→display, wardrobe→container+storage, etc.)
   - Validates every tag against `data/library/tags/` + item vocabulary
3. Apply, then run task-323 lint — checks 3/4 must stay clean
4. Document the convention in `docs/virtualWorld/Library System/`
   (Library System Overview.md or a new short page)

## Design Decisions to Settle During Work

- Does `display` need engine semantics now (e.g. `put X on rack` validation),
  or is it population-only metadata? → Start population-only; engine behavior
  can ride existing spatial edges.
- Mannequins: display furniture that "wears" items via `equipped`-style edges?
  → Defer; note as task-9 phase-2 idea.

## Files

- `data/library/tags/*.json` (new tag files)
- `data/library/areas/*.json` (tag backfill)
- `data/library/items/*.json` (furniture role/domain tags)
- `tools/tag_domains.py` (new script)
- docs update under `docs/virtualWorld/Library System/`

## Verification

- `python tools/lint_library.py` → 0 errors, area coverage warning gone
- Spot-check: a `clothing`-tagged area + `display` rack + clothing items form
  a connected chain (the exact query task-9 will run)

## Dependencies

- Blocked by: task-323 (lint validates this pass's output)
- Blocks: task-9 implementation (chain needs real domain tags to walk)
