---
type: task
status: todo
area: graph
priority: medium
wiki: "[[World Building/Graph System]]"
---

# Task 290 - Template Variants & Override Tracking

## Status

Todo - follow-up to task-289, not started.
The "don't clobber protected data" intent already exists in the **World→Library**
direction as an automatic guard (empty world values never erase library data in the
sync modal, diff-modal shows protected fields un-checked) - added 2026-08-20.
task-290 makes this an author-declared `overrides` feature for Library→World.
See **task-317**.

## What

Add two optional layers on top of the basic template-link system from task-289:

1. **Template variants** - let a library file define a base template plus named variants (e.g., `Task 3 - main area` is base; `closed door` and `open door` are variants with `parent_template`).
2. **Override tracking** - let a node declare which fields it has customized, so sync only refreshes non-overridden fields.

## Why

- `labs.json` has near-duplicate rooms that are really state variants of the same base space (e.g., `Task 3 - area 1 closed door` / `open door`). Variants make this intentional and maintainable.
- Authors sometimes want to localize a room (custom description) but still receive mechanical updates (new triggers, tags). Override tracking enables partial sync without breaking the template link.

## Design Decisions

1. **Variants are first-class in the library**
   - A library file can declare a `base` block plus a `variants` map.
   - Each variant has `name`, optional `parent_template`, and a partial definition that overrides the base.
   - When placing from library, the author picks either the base or a named variant.
   - Syncing a variant first applies the base sync, then re-applies the variant's overrides on top.

2. **`template_ref` replaces flat `library_id`**
   - Node stores:
     ```
     "template_ref": {
       "library_id": "task_3_area",
       "variant": "closed_door",   // null or omitted = base
       "linked_fields": ["name", "triggers", "properties.tags"],
       "overrides": {
         "description": "Custom flavor text that shouldn't be clobbered."
       }
     }
     ```
   - `linked_fields` is optional; if absent, all mutable fields sync.
   - `overrides` is optional; if present, those fields are excluded from sync unless the author explicitly chooses "force sync overrides."

3. **Sync behavior with variants + overrides**
   - Sync order: base definition → variant overrides → node overrides excluded.
   - If a node has `overrides`, sync returns a warning: "3 fields protected by overrides, skipped."
   - Break-link removes the entire `template_ref` block and converts overridden fields back to plain node fields.

4. **Frontend UX**
   - Library browser shows a tree: base → variants. Author can click "Place Base" or "Place Variant: Closed Door."
   - Inspector shows: "Linked to `task_3_area` (variant: closed_door). 2 fields overridden." with links to view/edit overrides.
   - Sync dialog offers: "Sync all linked fields" vs "Force sync (include overrides)."

## Implementation Steps

1. **Library schema extension**
   - Add `base` + `variants` support to library loader.
   - Variants resolve against their parent at load time; placed nodes store the resolved `library_id` + `variant`.

2. **Backend: `template_ref` structure**
   - Replace flat `library_id` with `template_ref` dict on nodes.
   - Migration: existing `library_id` fields are wrapped into `template_ref` on first read.

3. **Backend: override-aware sync**
   - `engine/sync.py` respects `linked_fields` and `overrides` during sync.
   - Returns structured diff: `{ updated: [...], skipped_overrides: [...], already_current: true }`.

4. **Frontend: variant picker + override editor**
   - Library browser: variant tree + place buttons.
   - Inspector: override list with edit/delete per field.

5. **Testing**
   - Variant sync: base changes propagate to variant nodes, variant-specific fields preserved.
   - Override sync: protected fields skip, unprotected fields update.
   - Break-link with overrides: overrides flatten into plain node fields.

## Out of Scope

- Bulk variant creation from existing near-duplicate nodes (could be a later migration tool).
- Conflict resolution when base and variant edit the same field (variant wins by design).

## Why

task-289 added template links; task-317 and reconnaissance show the "don't clobber protected data" guard already exists in World->Library direction (engine/sync.py has template_ref() and override/locked handling). What remains is the author-declared Library->World direction: template variants (base + named variants like closed/open door) and per-node override tracking with explicit control over sync. This makes near-duplicate rooms intentional and maintainable (e.g. labs.json variants) while allowing authors to localize fields without blocking mechanical updates.

## How

Reuse existing sync/override mechanisms where present; extend to variants.

1. **Library schema extension**: extend library loader to support `base` + `variants` map with `name`, optional `parent_template`, partial definition. Variants resolve against parent at load time; placed nodes store `template_ref.library_id` + `variant`.
2. **Backend template_ref**: replace flat `library_id` with `template_ref` dict containing `library_id`, `variant` (null/omitted for base), optional `linked_fields`, optional `overrides`. Migrate existing `library_id` to `template_ref` on first read.
3. **Backend override-aware sync**: extend engine/sync.py to respect `linked_fields` and `overrides`. Sync order: base definition -> variant overrides -> node overrides excluded. Return structured diff with `updated`, `skipped_overrides`, `already_current`. Add "force sync overrides" option. Break-link removes `template_ref` and flattens overrides.
4. **Frontend**: Library browser shows tree base -> variants with Place Base/Place Variant buttons; Inspector shows link/variant/override count with edit/delete; Sync dialog offers sync all vs force sync overrides.

## Steps to verify

1. Variant resolution and placement
   - expected: Library shows base with named variants; placing variant stores `template_ref.variant` and resolves base+variant correctly.
   - observed: Not run live; reconnaissance shows template_ref/override handling exists but no variants/base+variants resolution or UI variant picker detected.

2. Variant-aware sync
   - expected: base changes propagate to variant nodes; variant-specific fields preserved; variant overrides applied after base.
   - observed: Not run live; variant sync logic not implemented.

3. Override tracking
   - expected: customizing a field marks it in `overrides`; sync skips overridden fields and reports count; force sync includes overrides.
   - observed: Not run live; override structure exists in engine/sync.py but full override tracking flow not verified end-to-end.

4. Break-link with overrides
   - expected: break-link removes `template_ref` and flattens overridden fields into plain node fields.
   - observed: Not run live; not implemented.

## Acceptance

- [ ] Library loader supports `base` + `variants` and resolves them on load.
- [ ] `template_ref` dict replaces flat `library_id` with migration path; variant identity persists.
- [ ] engine/sync.py performs base->variant->overrides order with `skipped_overrides` reporting and force-sync option.
- [ ] Library browser shows variant tree; Inspector shows overrides; Sync dialog supports both modes.
- [ ] Break-link flattens overrides into plain node fields.

## Files

- `engine/sync.py` - extend template_ref/override handling for variants and variant-aware sync
- Library loader/schema (data/library loading code) - support `base` + `variants` resolution
- Node serialization/migration - wrap flat `library_id` into `template_ref` on read/write
- Frontend: `static/js/library/*` (browser) - variant tree and place buttons
- Frontend: `static/js/inspector/*` - show variant/overrides and sync dialog options
- `tests/` - variant sync, override sync, break-link with overrides (add tests)

## Browser UI and intended live verification

Intended UI home: Library Browser → open a base template → choose its named variant (for example `closed door` or `open door`) → place/sync it into a scenario → inspect the node's override fields.

Current availability: the card proposes named template variants and per-node override tracking on top of task-289's template links. Variant selection and override-aware sync are not claimed as available today.

Live steps when available:
1. Open the base `Task 3 - main area` template and select `closed door`; preview it before placing.
   - expected: the preview shows the closed-door variant's declared fields and identifies its base template; no scenario node is written before Apply.
2. Place the closed variant, customize one field on the node, then sync the base template.
   - expected: non-overridden fields refresh from the template; the explicitly overridden field remains unchanged.
3. Switch to the `open door` variant and inspect the resulting preview and placed node.
   - expected: the variant-specific state changes to open while shared base fields remain inherited.
4. Reopen the scenario after save/reload and inspect the selected template/variant and overrides.
   - expected: variant identity and the node's override declaration round-trip independently; no customized value is silently overwritten.

This section is not a claim that planned UI exists or works today.


## Reconnaissance (2026-10-20)

- Measured: engine/sync.py has template_ref() and override/locked handling; no variants/base+variants resolution or UI variant picker detected.
- Count: template_ref appears in engine/sync.py; variant-selection logic not present.
- Verdict: PARTLY_DONE structurally (overrides/locked), full variant system (base+variants, picker, variant-aware sync) NOT implemented. Keep todo.
