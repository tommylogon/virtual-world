---
type: task
status: todo
area: library
priority: medium
wiki: "[[Library System/Library System Overview]]"
---

# task-509: Library - batch-generate triggers for selected items

**Filed:** 2026-09-24
**Related:** 508, 506, 424
**Depends on:** 508 - the depletion contract must be settled first, or a batch run
would write (or deliberately omit) the wrong depletion on 505 items at once.

## What

Let the author **select N library items and run the trigger suggester across the
whole selection**, with a reviewable diff before anything is written - instead of
opening each of the 505 items and clicking "⚡ Suggest" one at a time.

## Why

The pieces exist but are strictly per-item:

- The suggester buttons live in the node/editor pane
  (`static/js/inspector/trigger-helpers.js:154-155`), and the item editor calls
  them for the open item (`static/js/item-library.js:628`).
- The one multi-item selection the library has is for **placement only**:
  `_multiSelect` / `_checkedIds` are switched on by `openForRoom`
  (`item-library.js:59-69, 162-174, 192-196`) and clear on close.
- `static/js/shared/trigger-suggest-diff.js` already exists to review a proposed
  trigger set, and `trigger-helpers.js` even has a *batch* endpoint - but only for
  the several trigger types of **one** node (`trigger-helpers.js:564`).

So nothing can say "these 65 tag-only edible items need consumption triggers -
suggest them all and show me the diff". That is exactly the job task-506 needs.

## How

- **Selection mode** that is independent of placement: an action bar appears when
  items are checked ("N selected"), reusing `_checkedIds` and `renderList`'s
  `_multiSelect` path rather than inventing a second selection model.
- **Two run buttons** in the action bar:
  - `⚡ Suggest triggers (N)` - the offline heuristic
    (`ItemLibraryTriggerSuggester`), instant, no LLM.
  - `✨ Suggest (AI) (N)` - queued through the existing per-item AI route with
    bounded concurrency and a progress indicator.
- **Review before write.** Heuristic and AI results both stage into the existing
  diff view (`trigger-suggest-diff.js`); nothing is persisted until Apply. The
  review lists per-item `before → after`.
- **Policy for already-authored items** (the 13 that have triggers): default
  **skip and report**, with an opt-in "replace existing" that only applies to the
  checked set. Never silently overwrite hand-authored content.
- **Policy for the depletion contract:** the batch must not fight task-508 - until
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

## Steps to verify

- JS unit (`tools/unit/run.cjs`): selecting N items yields N staged sets; existing
  triggers are skipped by the default policy; re-run is idempotent.
- Manual: run over the 65 tag-only edible items; Apply writes one `on_eat`/`on_drink`
  per item, reviewed in the diff, and `python tools/tasks.py validate`-style lint
  still passes for the library.

## Reconnaissance (2026-10-02) - NOT started; dependency resolved

- **task-508 is settled (fork A, in review):** the engine auto-decrements
  `uses` on `eat`/`drink` (`engine/items/consume_actions.py::_spend_uses`), and
  `trigger-suggest-ai.js:122` / `consumable-triggers.js` already assume that.
  So the batch must **not** emit hand `adjust_uses` - the existing heuristic
  output is already correct, and the `uses_above 0` guard is meaningful. No
  policy fork remains.
- Existing per-item pieces to reuse: `static/js/item-library.js`
  `suggestTriggers` (`:613-700`, heuristic + AI into
  `TriggerSuggestDiff`), the hidden `lib-item-triggers` field,
  `_refreshEditorWithTriggers`, `_multiSelect`/`_checkedIds` (`:59-69`,
  `:162-196`), and `static/js/shared/trigger-suggest-diff.js`.
- Plan: a selection action bar (independent of `openForRoom` placement) that
  runs `ItemLibraryTriggerSuggester` per checked id, stages one set per item
  into `TriggerSuggestDiff`, persists only on Apply via
  `ApiClient.saveLibraryItem`, default-skips items that already have triggers
  (opt-in "replace existing"), and reports
  `N applied · M skipped · K failed`. Idempotent by diffing against the item's
  current triggers.
- This touches `static/js/item-library.js` (already modified here for task-636)
  and `static/js/shared/trigger-suggest-diff.js`; coordinate with
  `wt/items-library` before landing both.

## Files

- `static/js/item-library.ts` - the per-item "Suggest" buttons (`:633-634`) and
  `suggestTriggers()` (`:760`), plus the selection state `_multiSelect` /
  `_checkedIds` and the `openForRoom` placement path
- `static/js/shared/trigger-suggest-diff.js` - `TriggerSuggestDiff`, the
  per-item before/after review surface the batch would stage into
- `static/js/shared/trigger-suggest-ai.js` - the AI suggester, including the
  `uses_above 0` guard that assumes task-508's auto-decrement
- `static/js/item-consumable-triggers.js` - the depletion-trigger authoring
  that shares the same guard
- `engine/items/consume_actions.py` - `_spend_uses`, the auto-decrement the
  batch must not duplicate
- `data/library/items/` - the 2,208 item records the batch would write back

## Browser UI and intended live verification

Intended UI home: Library Browser → check several item rows → selection action bar → **Suggest triggers (N)** or **Suggest (AI) (N)** → per-item diff → Apply. Selection reuses the library's existing checked-item state.

Current availability: the card describes the single-item “⚡ Suggest” flow and proposes batch selection, progress, diff review, and explicit replacement. Batch trigger generation is not claimed as available today.

Live steps when available:
1. In Library Browser, select three items: one without triggers, one with `on_eat`, and one with another authored trigger. Inspect the selection bar and run the offline heuristic.
   - expected: the bar reports three selected; the diff proposes triggers for the empty item and skips/counts the two already-authored items by default.
2. Review every before/after row without applying.
   - expected: no library entry changes before Apply; each suggested trigger is associated with the correct item.
3. Apply, close and reopen the Library Browser, then run the heuristic on the same selection again.
   - expected: the applied data persists and the rerun creates no duplicate triggers.
4. Repeat with AI unavailable and then with AI enabled; watch progress while the browser remains responsive.
   - expected: unavailable AI offers the heuristic path; enabled AI reports per-selection progress and its result appears in the same review diff before write.
5. Select an item with existing depletion triggers and inspect its proposed diff.
   - expected: task-508's depletion decision is preserved; replacement requires an explicit opt-in.

## Reconnaissance (2026-10-20) - still valid

Re-checked on 2026-10-20. The multi-select state exists (`_multiSelect`, `_checkedIds` in `static/js/item-library.js`) but only for placement; no bulk suggest-triggers action bar and no per-item staging across a selection:

- `rg` for "Suggest triggers" / batch suggest in `static/js/item-library.js` returned 0 hits.
- `static/js/shared/trigger-suggest-diff.js` still single-set oriented.

Verdict: card accurate. Kept in todo.
