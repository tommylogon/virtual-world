---
type: task
status: todo
area: ui
priority: medium
related: [task-777, task-778, task-340, bug-46]
blocked_by: [task-777]
---

# task-779: Persist the event stream as structured records, not HTML strings

**Filed:** 2026-10-11
**Related:** task-777, task-778, task-340, bug-46

<!-- deps:start -->
**Blocked by:** [[task-777-event-stream-export-json-jsonl-formats-and-one-consolidated-export-modal-tick-sequence-range-actor-area-scope-filter-honesty]]
**Related:** [[task-777-event-stream-export-json-jsonl-formats-and-one-consolidated-export-modal-tick-sequence-range-actor-area-scope-filter-honesty]], [[task-778-standalone-event-stream-reader-cli-query-an-exported-run-without-the-app]], [[task-340-event-stream-v2]], [[bug-46-event-log-export-mixes-worlds-client-stream-is-not-per-world]]
<!-- deps:end -->

## What

Persist the event stream as structured records instead of HTML strings, so a run's log is complete and queryable rather than capped and re-parsed.

Today `StreamPersistence.persist()` stores one IndexedDB record per row holding `child.outerHTML` (`static/js/stream/stream-persistence.ts:52`, `static/js/storage.ts:288` - `{ id, html }`), capped at 2000 rows, while the DOM itself is trimmed at 5000 (`event-stream.ts:69`). Restore re-renders those strings through `Lit.unsafeHTML` (`stream-persistence.ts:90`).

Change the persisted shape to the event record task-777's projection already builds (`{ seq, tick, time, day, turn, actor, area, type, text, outcome?, payload? }`), render the DOM from records on restore, and keep the cap as a storage decision rather than a format one.

## Why

The user-facing goal behind task-777 is "find out what happened during a run". Three things block it today, all with the same root:

1. **The log is capped before you can export it.** 2000 persisted rows / 5000 DOM rows means a long run's beginning is gone at reload, and no export can recover what was trimmed. An export is only ever a window.
2. **HTML is a lossy, parse-y source for a queryable artifact.** task-777 projects records out of the DOM at export time; the same records could simply BE the persisted form. Persisting HTML and re-deriving structure on every export is the second source of truth AGENTS.md warns about, in the opposite direction.
3. **Restore re-renders 2000 nodes through `unsafeHTML`.** Records render once from data; the HTML round-trip also means any DOM-only state (collapse, story mode) has to be re-derived after the fact, which is what `rebindAll` and the `_lineSeq` regex rebuild exist for.

bug-46 already established that these rows are per-world and unsalvageable across worlds, so the store is already treated as disposable session state - which makes a shape change cheap.

## How

Depends on task-777's projection: `projectStreamRows()` becomes the single writer for both the export path and persistence, so there is one record shape in the codebase.

- `storage.saveEventLog` / `loadEventLog` take records instead of HTML strings. The store's `{ id, html }` rows become `{ id, ...record }`; a stored-log version key (same pattern as the existing `event_log_world` config key) drops or migrates pre-change logs rather than half-reading them.
- Restore builds DOM from records: one renderer per `type` (the inverse of the projection), reusing the existing bubble construction where possible rather than a new parallel path.
- What must survive the round-trip, verified live: turn-card grouping and collapse state, the area filter, the actor roster (`_knownActors`), `_lineSeq` continuity, story mode, and the raw-LLM chip payloads.
- The cap becomes explicit and documented (rows or bytes), and the export no longer inherits it silently.
- Keep the existing per-world drop behaviour from bug-46 intact.

## Steps to verify

1. Run a session, reload the page, export as JSONL.
   - expected: the exported records match what the same range produced before the reload, including `seq` continuity and raw-LLM payloads.
   - observed: ___
2. Collapse a turn card, set an area filter, enable story mode, reload.
   - expected: all three states are restored; the actor dropdown is repopulated.
   - observed: ___
3. Load a log persisted by the OLD format (HTML rows).
   - expected: it is dropped or migrated cleanly - never half-rendered - and the app logs which.
   - observed: ___
4. Run past the old 2000-row cap.
   - expected: rows persist up to the new documented cap, and the export states the cap rather than silently truncating.
   - observed: ___

## Acceptance

- The persisted stream is records, not HTML strings; `storage.saveEventLog`/`loadEventLog` carry the record shape.
- One projection serves export and persistence - no second record shape.
- Reload round-trips grouping, collapse, area filter, actor roster, `_lineSeq`, story mode and raw-LLM payloads.
- Old-format logs are dropped or migrated cleanly, never half-rendered.
- The cap is explicit, documented, and surfaced in the export instead of silently truncating.
- bug-46's per-world drop behaviour is preserved.
- Gates green: `python tools/ts_convert.py check`.

## Files

- `static/js/stream/stream-persistence.ts` (record round-trip)
- `static/js/storage.ts` (`saveEventLog` / `loadEventLog` shapes)
- `static/js/ui/event-log-export.ts` (projection shared with persistence, from task-777)
- `static/js/event-stream.ts` (restore path, `_lineSeq`, roster)
- `docs/virtualWorld/UI & Settings/Event Stream.md` (persistence model, after verification)
