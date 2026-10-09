---
type: task
status: todo
area: ui
priority: medium
related: [task-673, task-674, task-369, task-384]
---

# task-760: Inspector AI Improve writes without preview; route it through the diff modal

**Filed:** 2026-10-09
**Related:** task-673, task-674, task-369, task-384

## What

InspectorHelpers.improveWithAI (static/js/inspector/helpers.ts) sends the LLM result straight to api.updateNode with no preview. The moment the model answers, description, actions, tags, uses, weight, current_state, action_costs and skill_check have already changed in the world. The same codebase already owns a preview widget — shared/diff-modal.ts — and the item library-refresh path uses it (InspectorItemView._refreshFromLibrary in static/js/inspector/item-view.ts, which calls DiffModal.show(...) then api.refreshFromLibrary). Improve is the one AI write path that skips it.

## Why

An LLM change to authored data is the case that most needs a before/after review: it can silently replace tags, flip actions, or rewrite a value the user believed was protected, and the user never sees it. docs/design/full-entity-editors.md states the rule that the inspector is a projection of the authoritative world model and every edit flows through one validated path; an unseen AI write is the exception that rule exists to prevent. The field-lock UI currently implies protected values while nothing shows what the model actually proposed, so the lock and the write disagree.

## How

Route improveWithAI through DiffModal.show(current, incoming, sections, {direction: 'to-world'}) — the same call _refreshFromLibrary already makes. Build current from the node's live properties and incoming from the parsed LLM result through the existing apply() builder; reuse the item section list in item-view.ts and the way/area equivalents. Apply only the sections the user keeps, in a single api.updateNode call so the whole-world undo stack reverts it in one step (routes/saveload.py pushes one snapshot per graph update; undo is whole-world, not diff-based). Keep the existing locked_fields gate in buildPrompt/apply so locked fields never reach the proposal. Do not add a second validator: the accepted update still goes through the same endpoint and engine/trigger_validator.py path.

## Steps to verify

1. Open an item with a description, press Improve with a configured LLM.
   - expected: a diff modal opens showing each proposed field as before -> after; Cancel writes nothing.
   - observed: TODO
2. Keep one changed section, drop the rest, press Update.
   - expected: only the kept section changes in the world; the rest is untouched.
   - observed: TODO
3. Lock a field (for example tags), press Improve.
   - expected: the locked field is absent from the diff and unchanged after apply.
   - observed: TODO
4. Apply an accepted change, then Undo (toolbar undo or POST /api/undo steps:1).
   - expected: one Undo restores the pre-apply state.
   - observed: TODO
5. Repeat for the way and area inspectors.
   - expected: identical preview flow, because improveWithAI is shared across item/way/area.
   - observed: TODO

## Acceptance

- [ ] Improve never writes to the world before the user approves a diff.
- [ ] The proposal renders before/after per field through shared/diff-modal.ts; no second modal is added.
- [ ] Locked fields stay out of the proposal and unchanged on apply.
- [ ] One accepted apply is one api.updateNode call, so one Undo reverts it.
- [ ] Item, way, and area Improve all use the shared flow.

## Files

- `static/js/inspector/helpers.ts`
- `static/js/inspector/item-view.ts`
- `static/js/inspector/way-view.ts`
- `static/js/inspector/area-view.ts`
- `static/js/shared/diff-modal.ts`
- `docs/design/full-entity-editors.md`
