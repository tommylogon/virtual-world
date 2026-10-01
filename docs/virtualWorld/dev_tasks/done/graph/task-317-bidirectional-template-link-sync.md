# Task 317 — Bidirectional Template-Link & Sync (World↔Library, unified)

## Status

**DONE (2026-10-01)**, decided and implemented as one unit with **task-289**.

Both halves are now in place, and the World→Library safety rules this card
lists as "already implemented, must be preserved" were left exactly as they were —
`_mergeEntry`/`_isEmpty` and the diff modal's clobber guard are untouched, and
that is deliberate: the two directions share one idea (library = templates,
world = linked instances) but not one file. Library→World is a **field
whitelist**; World→Library is a **"never let a bare instance erase curated
data"** rule. Merging them would have put a clobber guard where a whitelist
belongs.

See **task-289** for the full result, the live browser verification, and the
decisions taken. What changed for this card's half specifically:

- The **link has one definition** (`engine/sync.py`) instead of three different
  id-resolution behaviours across four node types.
- **Unlinking exists in both directions' vocabulary**: `library_id` can be
  removed, which is what makes an author-side override durable rather than
  dependent on remembering not to press Refresh.
- The World→Library half was **verified as intact**, not re-implemented.

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
