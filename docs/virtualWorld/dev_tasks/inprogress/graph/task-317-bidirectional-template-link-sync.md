# Task 317 — Bidirectional Template-Link & Sync (World↔Library, unified)

## Status

In progress — both halves partly live. World→Library: `world-sync.js` `_isEmpty`/
`_mergeEntry` (`:243-257`) + `diff-modal.js` clobber flag (`:267-330`). Library→World:
`refresh-to-world` now covers item/way/area/character (`routes/library_ops.py:750-769`).
Remaining: `break-template-link` endpoint + inspector UI (task-289), and variants /
override tracking (task-290, not started — `template_ref` is absent from the code).

## Goal

Make template linking a coherent, safe system in BOTH directions across all node
types (item, way, area, character):

- **Library → World** (task-289/290): link a node to a template, refresh template
  changes down, break the link; variants + override protection (task-290).
- **World → Library** (this task's new half): push a world copy up to the library
  WITHOUT clobbering richer template data with bare world instances.

## Why

The two directions were built independently and behave inconsistently:

- `refresh-to-world` (Library→World) used to support only **items and ways**
  (the old `routes/library_routes.py:482` returned 400 for areas/characters); it now
  covers all four types (`routes/library_ops.py:765-768`).
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

Library→World (from 289/290):
- ~~extend `refresh-to-world` to area + character~~ — done (`routes/library_ops.py:765-768`)
- `break-template-link` endpoint + inspector UI — **not done** (no code matches)
- per-type mutable-field whitelist — **not done** (inline per `_refresh_*`; no `engine/sync.py`)
- variants + override tracking, `template_ref` migration (task-290) — **not started**

## Verification

- Unit tests: both sync directions; empty-world-never-clobbers; refresh works on all
  4 types; break-link preserves node data; overrides skip on sync.
- E2E: sync a bare world item to a rich template → template fields survive; refresh
  a linked area/character from template → updates apply.
