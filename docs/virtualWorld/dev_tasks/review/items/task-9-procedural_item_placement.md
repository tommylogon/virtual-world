---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---
# Procedural Item Placement: Tag-Chain Area Population Engine

**Filed**: 2026-07-17  
**Rewritten**: 2026-08-21 (concept draft â†’ implementation plan after equip_slots/tag groundwork landed)  
**Priority**: Medium  
**Status**: Review — implemented 2026-09-23 (engine + route + MCP + editor button; see
Implementation). Consumed by task-398 (deterministic structure generation) and depended on
by task-438 (NL-editor region decomposition, which needs `engine/population.py`).

---

## Summary

Auto-populate areas with fitting items from the library by walking a three-level
tag chain: **area domain tags â†’ display/storage furniture that shares the domain
tag â†’ items that share it**, choosing the spatial edge per furniture role
(`in` for wardrobes/cabinets, `on`/`beside` for racks/shelves/tables).

This is the hub task for the procedural population work. Satellites:

| Task | Role | Depends on |
|------|------|-----------|
| task-326 | Character interest-tag data pass (+ dup char cleanup) | — |
| task-323 | Library lint validator (`tools/lint_library.py`) | — |
| task-324 | Domain tag schema + area/furniture tagging pass | task-323 |
| task-325 | Auto-dressing characters from interests | task-326 |
| **task-9** | **Population engine (this task)** | **323, 324** |

## Current State (verified 2026-08-21)

- âœ… All 60 wearable library items have `equip_slots` (tools/fix_item_equipment.py)
- âœ… Item tags lowercased/deduped; 204 distinct item tags exist
- âœ… `_spawn_library_item_node` (routes/library_routes.py:130) transfers `tags`,
  `equip_slots`, materializes `contents` recursively **with per-child spatial
  relations** (`_content_relation`: in/on/under/beside/behind/at) — old gap #2 is FIXED
- âœ… MCP tool `build_item_from_library` + route `library_place_item` exist
- âš ï¸ Areas: only 23/58 library areas have tags, and current values are *setting*
  flavored (`fantasy`, `school`), not domain flavored (`store`, `clothing`)
- âŒ No population module, no display-furniture role tag, no density/placement rules

## Design: The Tag Chain

Same domain tag at all three levels — matching is plain set intersection:

```
Area  "Clothing Store"   tags: [store, clothing]
  â””â”€ Rack                tags: [furniture, display, clothing]   â†’ items placed ON/BESIDE
  â””â”€ Wardrobe            tags: [furniture, container, storage, clothing] â†’ items placed IN
       â””â”€ Dress          tags: [clothing, outerwear]
```

1. Read target area's tags â†’ domain set D.
2. Find furniture in the area (or spawn it from library) whose tags âˆ© D â‰  âˆ… and
   which carries a role tag: `display` (surface placement) or `container`/`storage`
   (containment).
3. For each furniture piece, select candidate items: library items whose tags âˆ© D â‰  âˆ…,
   filtered by role compatibility (clothing on racks, small items in cabinets).
4. Place via existing relation edges; respect per-furniture capacity.

### Placement rules

- Edge choice by furniture role: `display` â†’ `on` (fallback `beside` when full);
  `container` â†’ `in`; bare floors/tables without role â†’ `at`/`on` sparingly.
- Surface items are already reachable by `take` (graph.py edge expansion) — no
  engine change needed for reachability.
- Density knobs (per-area item counts) read from `engine/runtime_config.py`
  DEFAULTS + SCHEMA so the Engine Config UI picks them up (see AGENTS.md gotcha).
- Idempotent: re-running on a populated area tops up to density instead of duplicating.
- Deterministic option: seedable RNG for reproducible scenario generation.

### Out of scope (later phases)

- LLM-hybrid selection ("what fits a Blizzard clearing?") — phase 2, after the
  deterministic chain works.
- NPC equipment generation from room context (guardsâ†’armor) — belongs with
  task-325 auto-dressing once this lands.
- Co-occurrence statistics — needs populated-world data first.

## Work Plan

1. Extract a public library/graph materialization service first. Route handlers
   may call it, and `engine/population.py` may call it, but the engine must not
   import a request-bound/private route helper such as `_spawn_library_item_node`.
2. `engine/population.py` (new, <600 lines per file-size rule):
   - `plan_population(graph, area_id, rng) -> [Placement(item_lib_id, furniture_id, relation)]`
   - `apply_population(...)` using the public materialization service + relation edges
   - capacity tracking per furniture node (count existing `in`/`on` children)
   - candidate indexes and archetype/role/exclusion filters; do not repeatedly
     scan the whole library or use raw tag overlap as sufficient relevance
3. **Furniture seeding** — population of an *empty* area must spawn the display/
   storage furniture itself before filling it: select library items tagged
   `furniture` + role tag + domain tag âˆ© area domains, place 1–3 pieces via
   spatial edges (`at`/`beside` walls is fine for v1), then run item fill.
   Without this step only pre-furnished areas benefit.
4. Route: `POST /api/populate/area/<node_id>` (density + seed params) in a routes module.
   Expose a planning/preview path as well; task-398 must be able to present
   unresolved tag pools and a graph-patch preview before applying a generated
   building.
5. MCP tool exposure in `mcp_server.py` (`populate_area`)
6. Editor button (area inspector) — thin UI pass, separate commit
7. Tests: fixture graph with tagged empty area; assert furniture gets seeded,
   relations chosen by role, idempotency, density cap (pattern:
   tests/test_item_actions.py fixtures)

## Implementation (2026-09-23)

Landed (uncommitted at time of writing):

- **`engine/population.py`** — `LibraryIndex` (tag → library id, 489 items/221 tags),
  `plan_population(area_tags, index, rng, ...)`, `apply_population(plan, spawn,
  relate, area_node_id)`. Pure + deterministic; no Flask imports. Unresolved
  domains are reported, never silently substituted.
- **`tools/tag_domains.py`** — task-324 domain/role tagging pass (dry-run default,
  `--apply`). 22 goblin areas + 27 furniture + 27 items; +14 tag files.
- **`routes/library_ops.py`** — public `materialize_library_item(app, library_id)`
  (work plan step 1) so the engine is not coupled to `_spawn_library_item_node`.
- **`routes/population.py` + `routes/population_ops.py`** — work plan step 4:
  `POST /api/populate/area/<area_id>` with `seed`, `furniture_max`,
  `items_per_area`, `preview`. Re-run safe: non-empty area → `already_populated`.
- **`mcp_server.py`** — work plan step 5: `populate_area` tool.
- **`static/js/inspector/area-view.js`** — work plan step 6: `🪄 Populate` button.
- **Tests** — `tests/test_population.py` (7) + `tests/test_population_route.py` (5).

Verified in-process (Flask test client): `area_storage_caves` previewed + applied
3 furniture + 6 items; second call idempotent. Live browser/server verification
pending (server was down).

### Deferred / follow-ups

- Density knobs not yet wired to `engine/runtime_config.py` SCHEMA (work plan
  note) — currently request params only.
- Raw tag intersection still admits generic matches (`interior`, `cave`); a
  domain-category filter on `LibraryIndex` would tighten relevance.
- Character equipment generation (task-325) and LLM-hybrid selection remain later
  phases.

## Verification

- `python -m pytest tests/ -q -k "not mcp and not emote"`
- Manual: populate the mansion kitchen + a store area; `look` shows items on/in
  furniture; `take` works on surface-placed items
- task-323 lint reports no dead tags introduced

## Refactoring Impact

Item creation lives in static/js/ui/create-modal.js, routes/library_routes.py,
engine/item_actions.py. Population logic goes in **engine/population.py** (new);
do not grow item_actions.py past the file-size rule.
