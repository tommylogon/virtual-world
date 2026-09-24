---
type: task
status: todo
area: library
priority: medium
---

# task-509: Library — batch-generate triggers for selected items

**Filed:** 2026-09-24
**Related:** 508, 506, 424
**Depends on:** 508 — the depletion contract must be settled first, or a batch run
would write (or deliberately omit) the wrong depletion on 505 items at once.

## Goal

Let the author **select N library items and run the trigger suggester across the
whole selection**, with a reviewable diff before anything is written — instead of
opening each of the 505 items and clicking "⚡ Suggest" one at a time.

## Problem

The pieces exist but are strictly per-item:

- The suggester buttons live in the node/editor pane
  (`static/js/inspector/trigger-helpers.js:154-155`), and the item editor calls
  them for the open item (`static/js/item-library.js:628`).
- The one multi-item selection the library has is for **placement only**:
  `_multiSelect` / `_checkedIds` are switched on by `openForRoom`
  (`item-library.js:59-69, 162-174, 192-196`) and clear on close.
- `static/js/shared/trigger-suggest-diff.js` already exists to review a proposed
  trigger set, and `trigger-helpers.js` even has a *batch* endpoint — but only for
  the several trigger types of **one** node (`trigger-helpers.js:564`).

So nothing can say "these 65 tag-only edible items need consumption triggers —
suggest them all and show me the diff". That is exactly the job task-506 needs.

## Design

- **Selection mode** that is independent of placement: an action bar appears when
  items are checked ("N selected"), reusing `_checkedIds` and `renderList`'s
  `_multiSelect` path rather than inventing a second selection model.
- **Two run buttons** in the action bar:
  - `⚡ Suggest triggers (N)` — the offline heuristic
    (`ItemLibraryTriggerSuggester`), instant, no LLM.
  - `✨ Suggest (AI) (N)` — queued through the existing per-item AI route with
    bounded concurrency and a progress indicator.
- **Review before write.** Heuristic and AI results both stage into the existing
  diff view (`trigger-suggest-diff.js`); nothing is persisted until Apply. The
  review lists per-item `before → after`.
- **Policy for already-authored items** (the 13 that have triggers): default
  **skip and report**, with an opt-in "replace existing" that only applies to the
  checked set. Never silently overwrite hand-authored content.
- **Policy for the depletion contract:** the batch must not fight task-508 — until
  508 decides, do not emit hand `adjust_uses` (the suggester's current contract),
  and once 508 lands, emit exactly what it specifies.
- **Report:** `N applied · M skipped (already authored) · K failed`, with the
  failed ids listed so the author can retry.

## Acceptance

- Checking items in the library shows a bulk bar; running the heuristic on the
  selection produces one trigger set per item, visible in the diff, and writes
  nothing until Apply.
- The AI path processes the selection without freezing the UI, shows progress,
  and degrades gracefully when the AI is unavailable (offer the heuristic).
- Items that already have `on_eat`/`on_drink` (or any triggers) are skipped by
  default and counted in the report; "replace existing" is explicit.
- A re-run on already-suggested items is idempotent (no duplicate triggers).
- The batch respects the task-508 depletion decision.

## Non-goals

- Redesigning the library UI (task-510).
- Per-item nutrition/restore tuning (task-506).
- Authoring triggers for non-item node kinds (ways/areas keep their per-node path).

## Verification

- JS unit (`tools/unit/run.cjs`): selecting N items yields N staged sets; existing
  triggers are skipped by the default policy; re-run is idempotent.
- Manual: run over the 65 tag-only edible items; Apply writes one `on_eat`/`on_drink`
  per item, reviewed in the diff, and `python tools/tasks.py validate`-style lint
  still passes for the library.
