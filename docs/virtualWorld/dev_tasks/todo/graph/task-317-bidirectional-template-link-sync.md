# Task 317 — Bidirectional Template-Link & Sync (World↔Library, unified)

## Status

Todo — ties together task-289 (Library→World) and task-290 (variants/overrides)
with the World→Library sync direction and the data-safety rules added 2026-08-20.

## Goal

Make template linking a coherent, safe system in BOTH directions across all node
types (item, way, area, character):

- **Library → World** (task-289/290): link a node to a template, refresh template
  changes down, break the link; variants + override protection (task-290).
- **World → Library** (this task's new half): push a world copy up to the library
  WITHOUT clobbering richer template data with bare world instances.

## Why

The two directions were built independently and behave inconsistently:

- `refresh-to-world` (Library→World) only supports **items and ways**
  (routes/library_routes.py:482 returns 400 for areas/characters).
- The sync modal (World→Library) originally did a **full overwrite**: a bare world
  copy (empty description, no triggers) nuked the curated template — the `brass_key`
  incident. Fixed 2026-08-20 with a merge guard (empty world values no longer erase
  library data) + diff-modal clobber protection.
- task-289/290 describe the Library→World half; nothing tracks the World→Library half.

## Design Decisions

1. **Two directions, one mental model**: library = templates; world = unique linked
   instances. `library_id` (or task-290's `template_ref`) is the link in both directions.
2. **World→Library safety rules** (already implemented, must be preserved):
   - `_silentSave` merges: non-empty world values win; empty world values ("" / [] / {})
     never erase library data (world-sync.js `_mergeEntry`).
   - Diff modal: a field where the library has data but the world copy is empty shows
     as a guarded "clobber" — not pre-checked, amber ⚠, hover warning
     (diff-modal.js `clobber` flag).
3. **Library→World generalization** (pull from 289/290): extend `refresh-to-world`
   to areas and characters; add `break-template-link`; per-type mutable-field whitelist.
4. **Override tracking (290)** is the author-visible layer of the same "don't clobber"
   rule: `template_ref.overrides` protects fields from sync in Library→World, just as
   the merge guard protects them in World→Library.

## Scope

World→Library (implemented 2026-08-20 — verify + keep):
- world-sync.js `_mergeEntry` + `_isEmpty` guard on bulk sync
- diff-modal.js clobber detection / uncheck-by-default on empty-world-over-library

Library→World (from 289/290, NOT yet generalized):
- extend `refresh-to-world` to area + character
- `break-template-link` endpoint + inspector UI
- per-type mutable-field whitelist (engine/sync.py, task-289 step 1)
- variants + override tracking, `template_ref` migration (task-290)

## Verification

- Unit tests: both sync directions; empty-world-never-clobbers; refresh works on all
  4 types; break-link preserves node data; overrides skip on sync.
- E2E: sync a bare world item to a rich template → template fields survive; refresh
  a linked area/character from template → updates apply.
