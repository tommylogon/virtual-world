---
type: task
status: todo
area: emotions
priority: medium
blocked_by: [task-691]
related: [task-714, task-757]
---

# task-756: Move emotion editing into the Mind view; the memory-edit modal is not its home

**Filed:** 2026-10-09
**Related:** task-691 (Mind dashboard), task-714 (character mind panel), task-757 (dead-cluster removal)

## What

Relocate per-memory emotion editing (label + intensity) from the memory-edit
modal into the Mind view (`inspector/mind-view.ts`), which is becoming the
character's mind surface (task-691 stage 4) and will supersede the memory editor.

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

Confirm the Mind view should take over memory *editing* (not just the read-only
dashboard it is today) before this is built. If yes, the move is:

1. Lift the grouped emotion picker + intensity control from `memory-view.ts`
   (the `memory_emotions` UI) into the Mind view's memory detail panel.
2. Save via the existing `updatePlayerMemory(charName, id, {memory_emotions})`.
3. Remove the editor from the memory modal (leave it a viewer), so there is one home.

## Acceptance

- [ ] Emotion editing (label + intensity, multiple per memory) lives in the Mind view.
- [ ] It writes the same `memory_emotions` field via `updatePlayerMemory` — no new store.
- [ ] The memory-edit modal no longer owns the editor (one home).
- [ ] `build:ts`, `typecheck`, unit clean.

## Files

- `static/js/inspector/mind-view.ts` (destination)
- `static/js/inspector/memory-view.ts` (current editor: `memory_emotions` picker)
- `static/js/api-client` (`updatePlayerMemory` / `addPlayerMemory`)

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO
