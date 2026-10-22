---
type: task
status: done
area: emotions
priority: medium
blocked_by: [task-691]
related: [task-714, task-757, task-820]
---

# task-756: Move emotion editing into the Mind view; the memory-edit modal is not its home

**Filed:** 2026-10-09
**Related:** task-691 (Mind dashboard), task-714 (character mind panel), task-757 (dead-cluster removal), task-820 (tabbed container)

<!-- deps:start -->
**Blocked by:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]]
**Related:** [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-757-enable-nounusedlocals-and-clear-the-unused-symbol-backlog-three-orphaned-ui-wirings-restored]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]]
<!-- deps:end -->

## What

Per-memory emotion editing (label + intensity, multiple) now lives in the Mind view's memory detail; the memory-edit modal no longer owns it. Writes the same `memory_emotions` field via `updatePlayerMemory` - no new store.

## Reconciliation (2026-10-09) — the premise was half true

The card was filed from a dead code cluster (`emo`/`emoLbl`/`emoInt`/`emoOptions`/
`emoOpts`) in `inspector/memory-view.ts` that rendered no field. That cluster was a
**dead duplicate**: the memory-edit modal already edits a *richer* emotion set
through `memory_emotions: [{label,intensity}]` — the grouped picker at
`memory-view.ts:17-18, 418-419`, saved in the payload at `:572` via
`updatePlayerMemory`/`addPlayerMemory`. The dead cluster was removed in task-757.

So there is **no missing emotion editor to add** — the feature exists, in the memory
modal. Relocating it is a UI move that belongs with the Mind view takeover.

## Why deferred

Adding an emotion editor to the Mind view *now* would create a second editing
surface over the same `memory_emotions` field while the memory modal still owns the
memory list and add/edit flow — i.e. two places to edit one memory, which is the
"second source of truth for a surface" the repo warns against. The clean cut is:
when task-691/714 make the Mind view own the memory list, move the editor with it.

## Decision needed

RESOLVED 2026-10-13: yes — the Mind view takes over memory *editing*, not just the
read-only dashboard (Bio survives as the character's definition surface; the Mind
panel owns the mind). The move is:

1. Lift the grouped emotion picker + intensity control from `memory-view.ts`
   (the `memory_emotions` UI) into the Mind view's memory detail panel.
2. Save via the existing `updatePlayerMemory(charName, id, {memory_emotions})`.
3. Remove the editor from the memory modal (leave it a viewer), so there is one home.

## Acceptance

- [x] Emotion editing (label + intensity, multiple per memory) lives in the Mind view.
- [x] It writes the same `memory_emotions` field via `updatePlayerMemory` - no new store.
- [x] The memory-edit modal no longer owns the editor (one home).
- [x] `build:ts`, `typecheck`, unit clean (`python tools/ts_convert.py check` green).

## Files

- `static/js/inspector/mind-view.ts` (the editor)
- `static/js/inspector/memory-view.ts` (the editor removed)
- `static/js/types/globals.d.ts` (`updatePlayerMemory` declared)

## Browser UI and intended live verification

Intended UI home: Character Inspector → Mind → select a memory → its detail panel → “Save feelings”. The legacy memory-edit modal is a read-only viewer for emotions.

Current availability: Both locations were live-checked on localhost:4444 on 2026-10-13: Mind saved `memory_emotions` through `updatePlayerMemory`, and the memory modal rendered without `#mem-editor-emotions`.

Live steps when available:
1. Select a character with a memory, open Mind, select that memory, choose anger at intensity 8, and click “Save feelings”.
   - expected: the memory's detail shows anger at 8 after saving, and the same value remains after closing and reopening the detail.
2. Open the memory-edit modal for that same memory.
   - expected: the modal does not offer an emotion picker or an emotion save control, so there is one editing home for `memory_emotions`.
3. Change the memory text in its existing editor and save, then return to Mind.
   - expected: the text edit leaves the saved emotion value unchanged.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Why

The Mind view is becoming the character's mind surface (task-820) and supersedes the memory editor. Adding the editor there while the modal still owns it would put one field in two homes - the "second source of truth for a surface" the repo warns against. So the editor moves with the surface.

## How

`mind-view.ts` renders the emotion editor in the memory detail (`#mind-mem-emotions` + a `💾 Save feelings` button). The picker is reused, not copied: `InspectorMemory._attachEmotionSelector` (already exposed) is called on the container, and Save reads `InspectorMemory._emoSelected` and calls `ApiClient.updatePlayerMemory(charName, id, { memory_emotions, emotion })` - the same field the modal used. `memory-view.ts` lost the "😊 Emotions (multiple)" section, the `_attachEmotionSelector` call, and the `memory_emotions` / `emotion` payload lines, so the modal no longer writes emotions (editing a memory's text cannot clobber them). The gen-memory flow keeps its own picker. `ApiClient.updatePlayerMemory` was added to the declared surface in `static/js/types/globals.d.ts`.

## Steps to verify

1. Open a memory in the Mind panel and set two emotions with intensities.
   - expected: saved via `updatePlayerMemory` to `memory_emotions`; reopening shows the same values.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. Selecting a memory renders the picker in `#mind-mem-emotions`; clicking `💾 Save feelings` with `InspectorMemory._emoSelected = [{anger,8}]` called `updatePlayerMemory` with `{ memory_emotions: [{label:"anger",intensity:8}], emotion: {...} }` (no error) and the memory round-tripped with those emotions. (Probe emotions cleared.)
2. Open the memory-edit modal.
   - expected: it is a viewer; no emotion editor remains there.
   - observed: VERIFIED 2026-10-13. `InspectorMemory.showMemoryEditor(name, id)` renders a modal with no `#mem-editor-emotions` element.
