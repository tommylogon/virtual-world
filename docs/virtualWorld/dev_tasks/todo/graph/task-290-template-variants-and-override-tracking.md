---
type: task
status: todo
area: graph
priority: medium
---

# Task 290 — Template Variants & Override Tracking

## Status

Todo — follow-up to task-289, not started.
The "don't clobber protected data" intent already exists in the **World→Library**
direction as an automatic guard (empty world values never erase library data in the
sync modal, diff-modal shows protected fields un-checked) — added 2026-08-20.
task-290 makes this an author-declared `overrides` feature for Library→World.
See **task-317**.

## What

Add two optional layers on top of the basic template-link system from task-289:

1. **Template variants** — let a library file define a base template plus named variants (e.g., `Task 3 - main area` is base; `closed door` and `open door` are variants with `parent_template`).
2. **Override tracking** — let a node declare which fields it has customized, so sync only refreshes non-overridden fields.

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

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

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
