---
group: Library
---
# Domain Tag Schema + Area/Furniture Tagging Pass

## Outcome (verified 2026-09-22) — complete

All four work-plan steps are addressed. The population chain now has real domain data
on the area side, which is what task-9 → task-398 → task-438 were waiting on.

**Landed this pass:**
- **All 35 previously-untagged library areas tagged** (plus the 22 goblin-camp areas
  from the first pass). `tools/lint_library.py` `area_tag_gaps` is now **empty**
  (was: "35 areas have no tags"). 90/90 areas carry tags.
- `tools/tag_domains.py` extended with the full `AREA_DOMAINS` table (57 entries),
  domain tags on domain-specific furniture (`FURNITURE_TAGS`, 30 entries), and
  `ITEM_TAGS` for the new domains. **66 files changed** (35 areas, 19 items-as-furniture,
  12 items).
- **`--domains` implemented.** The flag was advertised in the module docstring and help
  but argparse never defined it; it now filters the pass to a comma-separated tag list
  (e.g. `--domains kitchen,library`), which is also how the incremental follow-up was
  applied.
- **9 new tag files created** this pass (`dining`, `bedroom`, `study`, `garden`, `loot`,
  `settlement`, `trade`, `mansion`, `interior`); 51 tags referenced by the tables now
  have metadata files.
- **`docs/virtualWorld/Library System/Domain & Role Tags.md`** written — the convention,
  the four tag kinds, the chain, the worked example, the tool usage, and the
  verification commands. Linked from [[Tags System]].

**Verified:**
- `python tools/lint_library.py` → `area_tag_gaps` gone; `singleton_tags` 88
  (was 87; +1 for `garden` on the single `garden_bench`, informational only).
- `python tools/tag_domains.py` (dry run) → idempotent, 0 further changes.

**Deliberately out of scope — these are not this task's checks:**
- **23 `dead_interests` errors.** `check_dead_interests` compares character
  `interest_tags` against the **item** tag vocabulary (`tools/lint_library.py:55-67`),
  *not* tag files. Creating tag files cannot clear them; they need either item tags or
  character interest edits. **Owned by task-326** (character interest-tag pass).
- **1 `missing_slots` error:** `items/broken_shield` is tagged clothing/armor with empty
  `equip_slots`. A one-line item fix, filed separately from the tag vocabulary work.
- **`singleton_tags` is informational.** A place domain legitimately on a single unique
  piece (one garden bench) is not a typo and must not be force-connected.
- The original verification target "509 + 9 = 518 registered tags" is **stale**: the
  library now holds **90 areas / 494 items / 66 characters**. Coverage is the metric,
  not a hardcoded tag count.

**Files changed this pass:**

| File | Change |
|------|--------|
| `tools/tag_domains.py` | `AREA_DOMAINS` → 57 entries; domain tags on furniture; `ITEM_TAGS` extended; `NEEDED_TAGS` covers every referenced tag; `--domains` implemented |
| `data/library/areas/*.json` | 35 areas tagged |
| `data/library/items/*.json` | 19 furniture + 12 items tagged |
| `data/library/tags/*.json` | 9 new tag files |
| `docs/virtualWorld/Library System/Domain & Role Tags.md` | new convention doc |
| `docs/virtualWorld/Library System/Tags System.md` | link to the new doc |

---

**Filed**: 2026-08-21
**Priority**: Medium
**Depends on**: task-323 (lint validates the result) — landed and re-run here.

## Summary

Establish the **domain tag convention** that powers task-9's population chain: the
*same* domain tag appears on areas, on display/storage furniture, and on items — then a
population pass is just set intersection down the chain. Register new tags in
`data/library/tags/`, backfill area tags, and role-tag furniture
(`display` vs `container`/`storage`).

## The Convention

```
Area  "Clothing Store"   tags: [store, clothing]
  └─ Rack                tags: [furniture, display, clothing]      → ON/BESIDE placement
  └─ Wardrobe            tags: [furniture, container, storage, clothing] → IN placement
       └─ Dress          tags: [clothing, outerwear]
```

Rules:

1. **Domain tags describe what a place is FOR** (`store`, `clothing`, `kitchen`,
   `library`, `occult`) — distinct from setting tags (`fantasy`, `school`, `modern`,
   `mansion`, `interior`) which say what world/where it is. Both can coexist on an area.
2. **Role tags on furniture**: `display` = surface placement target (racks, shelves,
   tables, mannequins); `container`/`storage` = containment targets. A piece may have
   both (dresser: `in` for drawers, `on` for top surface).
3. Every new tag gets a file in `data/library/tags/` with category/applies_to metadata.

The fuller statement of this convention now lives in
[[Library System/Domain & Role Tags]].

## Tag Schema (2026-09-17)

All pre-existing tags remain valid. New tags extend the schema with two optional arrays
while keeping every legacy field unchanged.

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

**No prefix namespace needed.** A single tag file carries all dimensions; the population
layer filters by `category` + `context` instead of inventing `domain_clothing` /
`concept_clothing` / `loot_clothing`.

## Work Plan

0. ~~Create the missing tag files~~ — done (9 files this pass, 9 in the first).
1. ~~Derive domain tags from the untagged area files~~ — done (35 areas, plus the camp).
2. ~~Script `tools/tag_domains.py` with per-area and per-furniture tables~~ — done.
3. ~~Apply, then run task-323 lint~~ — done; `area_tag_gaps` clean.
4. ~~Document the convention in `docs/virtualWorld/Library System/`~~ — done
   (`Domain & Role Tags.md`).

## Dependencies

- Blocked by: task-323 (lint validates this pass's output) — landed.
- Blocks: task-9 implementation (chain needs real domain tags to walk) — **now unblocked
  on the area side**; task-398's tag-aware population and task-438's region decomposition
  both depend on these tags existing.
