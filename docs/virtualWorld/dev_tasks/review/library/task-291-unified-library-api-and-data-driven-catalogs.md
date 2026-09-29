---
id: 291
title: Unified Library API + data-driven Conditions & Traits catalogs
status: review
priority: high
created: 2026-08-17
tags: [library, refactor, conditions, traits, api, data-driven]
---

# Unified Library API + data-driven Conditions & Traits catalogs

Part of **Library 2.0** (design: `docs/virtualWorld/Library System/Library 2.0 - Unified Library Design.md`).
Implements the Phase 1 backend consolidation and the conditions/traits data-driven migration.

## Summary

- **One library API.** `routes/items_registry.py` folded into `routes/library_routes.py` and deleted.
  All callers (browser, item editor, agent inspector, MCP server) now hit `/api/library/*`.
- **Conditions + Traits are now data-driven.** The hardcoded `CONDITION_DEFINITIONS`
  (`player.py`) and `TRAIT_DEFINITIONS` (`engine/traits.py`) become fallbacks that load from
  `data/library/conditions/*.json` and `data/library/traits/*.json` at import time.

## Files Changed

### Backend consolidation
- `routes/library_routes.py` — added `POST /api/library/<type>/<id>/rename` (write new + GC old,
  collision-safe), `POST /api/library/items/<id>/place` (moved from `/api/build/item-from-library`),
  unified `POST /api/library/refresh-to-world` (dispatches item/way by node type, prefers
  `library_id`), and wired `validate_tags_on_save` into the generic POST. Folded item build + item
  refresh helpers in. Refactored way refresh into `_refresh_way`/`_rebuild_triggers`.
- `routes/items_registry.py` — **deleted** (single character import now lives only at
  `/api/library/import/character/<id>`).
- `app.py` — removed `items_registry` registration; added `seed_condition_library()` +
  `seed_trait_library()` (non-TESTING).
- `static/js/api.js` + `static/js/inspector/agent-view.js` — migrated off `/api/registry/*` and
  `/api/build/item-from-library`.
- `mcp_server.py` — MCP tools (`import_character`, `build_item_from_library`, the registry list/add/
  delete tools) now proxy to `/api/library/*`.

### Data-driven conditions (`player.py`)
- `_load_condition_library()` runs at import (before derived constants commit). `_CONDITION_BASE`
  covers partial files; files merge over the hardcoded fallback so a truncated save can't wipe gates.
- **BOM-safe** (`utf-8-sig`) and **int-key coercion** for `symptoms`/`level_periodic`/
  `level_speed_mult` (JSON stringifies int keys; engine looks them up by int).
- `seed_condition_library()` writes the catalog to `data/library/conditions/*.json` on first run
  (only if the dir is empty).

### Data-driven traits (`engine/traits.py`)
- `_load_trait_library()` runs at import; existing traits merge over the code fallback; a brand-new id
  is accepted only if it declares `effects`/`grants_conditions`/`save_on`. This keeps UI-only marker
  traits (the `size_*` files, resolved by `engine/size.py`) out of `TRAIT_DEFINITIONS`.
- `seed_trait_library()` rewrites the legacy params-only files to the canonical full schema (migrated
  52 files → 46 canonical + 6 untouched `size_*`).

## Verification

- `node --check` + `py_compile` clean.
- Full suite green: **959 passed, 1 skipped** (baseline 955; +4 from migrated library tests).
- Live smoke (server :4444): `/api/conditions` returns the 17-entry data-driven catalog; `place` into
  an area; `rename` writes new id and GCs old; `refresh-to-world` applies selected sections; legacy
  `/api/registry/items` → 404. Test artifacts cleaned up.
- Data-driven round-trips: override `blind.json` → gate flips (`BLOCKING_CONDITIONS` recomputes);
  override `glutton.json` effects → catalog reflects 3.0; reverts restore.

## Status

**In Review — implemented 2026-08-17, static checks + full suite + live smoke pass.** Conditions &
traits are data-driven (`data/library/conditions/*.json`, `data/library/traits/*.json` are the editable
source, hardcoded dicts are fallback). Backend consolidation to a single `/api/library/*` done.

## Remaining (see design doc)

- Phase 2: schema-driven editor + editable-ID rename (already live for ways) + custom modals for all
  tabs; Conditions/Traits tabs now edit the real data-driven catalogs.
- Phase 3: delete `data/library/rooms` (first update `tools/migrate_legacy_triggers.py:224`, which still
  names `library/rooms/mansion.json` as an input), the IndexedDB `item_library` store, and the
  `main.js:132` inline save; orphan sweep; finish `Library System Overview.md`.
  **Two items moved out of this task on 2026-09-29:**
  - **The behaviours tab is no longer to be removed.** The design doc's "remove the tab/type" is withdrawn;
    the tab is fully built and its saves really land in `data/library/behaviours/`, while
    `engine/npc_behaviors.py:486` reads only `player.behaviors[]` — a live authoring path the engine ignores.
    Making the engine consume it (the traits treatment) is **task-590**. Do not execute the removal.
  - **Structures** are not in scope here. The engine and the five routes are done; the missing piece is a
    UI affordance, tracked by **task-591**.
  `Library System Overview.md` was partially corrected on 2026-09-29 (the "registry deletes files" claim, the
  6-type list, the "no live link" claim, the directory tree and per-type counts, and the two fabricated
  `load_registry` / `save_registry` samples). It still shows a removed item field (`effect_target`) and omits
  DiffModal, refresh-from-library, build-item-from-library and the condition catalog, so the rewrite is
  still open here.
