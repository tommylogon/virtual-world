---
type: task
status: review
area: ui
priority: medium
related: [task-340, task-347, task-61]
blocks: [task-778]
---

# task-777: Event stream export: JSON/JSONL formats and one consolidated export modal (tick-sequence range, actor/area scope, filter honesty)

**Filed:** 2026-10-11
**Related:** task-340, task-347, task-61

<!-- deps:start -->
**Blocks:** [[task-778-standalone-event-stream-reader-cli-query-an-exported-run-without-the-app]]
**Related:** [[task-340-event-stream-v2]], [[task-347-export-log-lint-guards]], [[task-61-event_stream_timestamps]]
<!-- deps:end -->

## What

Add JSON and JSONL export formats for the event stream, projected from the same DOM rows the Markdown export already walks - no new event model and no second source of truth.

Replace the three separate export code paths (the file button, the range modal, and the clipboard button in `static/js/ui/world-export.ts`) with ONE export modal that owns: range unit and from/to, actor scope, area scope, format (markdown | plain | json | jsonl), destination (file | clipboard), and a live "what you are exporting" summary. The three header buttons stay in place but open that modal pre-set: the file button = whole log to file, the clipboard button = whole log to clipboard, the range button = as today.

Range unit defaults to the tick sequence (the `[Tick N]` label from `_nextLineLabel()` / `_lineSeq`), which is the unit requested. Turn remains a selectable unit so the existing range button does not regress. The world clock tick stays a per-row field (`tick`) and is NOT a range unit.

Stream filters are respected by default - rows hidden by the kind chips, the actor dropdown, the area filter, or the search box are skipped exactly as today - with an explicit "ignore stream filters" escape hatch, and the summary names which filters are active so an export never silently drops rows.

Intentionally NOT in this task: the standalone CLI reader (task-778); any change to the persistence cap (exports are still bounded by what the DOM and IndexedDB hold - 5000 DOM rows, 2000 persisted); any backend event log (the client stream remains the source of truth).

## Why

The only queryable artifact today is Markdown prose. "What happened during a run" is answered by reading, not by asking: `jq 'select(.actor=="Lyrie")'` over a run is impossible. task-347's `tools/log_lint.cjs` greps text for exactly this reason and is the precedent for wanting structure.

Three buttons are three code paths, two of which duplicate the same DOM walk (`buildMarkdownLog` and `buildRangeLog` re-implement the same bubble emission). `world-export.ts` is already 708 lines and would blow past the 600-line rule with JSON builders added, so the export pipeline needs to move into its own module regardless.

The range modal advertises only "log: 17-17". It does not say which filters are active, so an export can silently omit the LLM payloads, an actor, or a whole area and the user finds out only by reading the file.

## How

New module `static/js/ui/event-log-export.ts` (classic script, `@module` header, script tag in `templates/index.html` before world-export, `python tools/js_module_index.py --check` green) holding three things: the row projection, the four renderers, and the modal. `world-export.ts` keeps `saveFileWithDialog` and delegates `exportEventLog` / `copyEventLogToClipboard` / `showRangeExport` into the new module, so the public surface (`WorldExport.*` and the three inline `onclick` handlers) is unchanged.

Row projection (`projectStreamRows(streamEl, opts)` -> event records) reads only what the DOM already carries:
- `data-actor`, `data-tick` (world clock), `data-type` (falling back to the `msg-bubble-<type>` class for rows like the task-448 chooser that set no `data-type`), `data-stream-area`, and `dataset.rawText` - the RAW text, not the story-mode-stripped `.bubble-text` the Markdown path reads, because a queryable log wants the data.
- The `[Tick N | HH:MM]` label: N is the sequence id and the range key; HH:MM is game time.
- The enclosing `.turn-card`'s `[Turn N | ...]` header and `.turn-card-actor`; `turn` is null for loose rows (system rows, area transitions, time gaps).
- The `outcome-*` class on result rows, and the `.rawllm-chip-header` / `.rawllm-chip-body` payload on visible raw-LLM chips. A collapsed chip body is `display:none` by COLLAPSE, not by filter - the payload is read regardless (the AGENTS.md "a hidden element is not a closed one" trap).
- Rows with `style.display === 'none'` are skipped unless "ignore stream filters" is set. A `msg-bubble-stream` chip ("thinking...") is transient - `finishStreaming` removes it - so an export taken mid-flight can contain one; type it `stream` and let it be.
- **Stream chrome vs stream messages - read the code, do not guess.** Three kinds of non-bubble child sit in `#event-stream` and the current walk treats them all the same way (badly):
  - `.timeline-scrubber` is pure chrome - it renders only empty segment divs (`stream-scrubber.ts:80-83`), so its `textContent` is empty and it exports as nothing. Skip it.
  - `.stream-scope-banner` is a MESSAGE, not a button and not chrome: `📌 Scoped to: <area>` (`stream-filters.ts:178`) with a clear affordance (`×`, L180) beside it. Same for `.stream-scope-empty` ("No events recorded in X yet...", L198). Project the label text and emit it as a message row (`type: 'scope'` / `'scope-empty'`) - it tells the reader the view was scoped when the log was taken, which the Markdown header does not record anywhere else.
  - `.turn-queue-strip` is chrome (a live status widget) and is NOT harmless. It persists across reloads - `stream-persistence.ts:52` saves every child's `outerHTML`, nothing strips a stale strip on restore, and `renderQueueStrip` reuses the existing node (`event-stream.ts:170`) - and its text (`⏭ up next: ...`) has no `.bubble-text`, so the `textContent` fallback exports it as a bullet. Measured: 0 of the exports in `data/exports/` contain one, which is a fact about those files, not proof it cannot leak. Skip it.
  - The defect in all three cases is the same: `emitBubble` falls back to `bubble.textContent` when a row has no `.bubble-text`, which glues whatever else lives in the element onto the message. That is why the real export at `data/exports/world_template_tick_613_event_log_2026-09-05T02-35-04.md:8` reads `- 📌 Scoped to: Weeping Willow Hollow×` - the message plus the clear affordance's glyph. The projection reads the label span, never the container's `textContent`.

Sequence ids are regex-scraped out of the label string in THREE places, with two different regexes for the same label: `world-export.ts:308` (`/\[\s*Tick\s+(\d+)\s*\|/`, for the filename), `world-export.ts:445` (`/Turn\s+(\d+)/`, for range bounds) and `stream-persistence.ts:94` (`/\[Tick\s+(\d+)\|/`, to rebuild `_lineSeq`). There is no `data-seq` attribute anywhere in `static/js` (measured: 0 matches). Stamp `data-seq` on the bubble where the label is emitted (the `_nextLineLabel()` call sites) and have the projection and the restore read the attribute, so the export stops parsing its own UI.

Event record shape: `{ seq, tick, time, day, turn, actor, area, type, text, outcome?, payload? }` - `seq` is the tick-sequence id (the range key), `tick` the world clock, `turn` null for loose rows, `outcome` only on results, `payload` only on visible raw-LLM chips. `day` is the in-game day parsed from the enclosing turn card's label when the engine exposes `game_day`, so jq can slice a run by day without re-deriving the calendar.

JSONL is one event object per line with no envelope, so `jq` works directly. JSON is an envelope: `{ schema: 1, scenario, exported_at, world_tick, range: {unit, from, to}, filters: {active..., ignored}, counts: {events, turns, actors, areas}, events: [...] }` - the `schema` version lets task-778's reader (and any future change) detect shape drift instead of guessing.

The modal warns before copying when the payload is large: exports in `data/exports/` run to 16.8 MB, and a clipboard write of that size is not reliably available in every browser.

Modal controls: unit select (Tick sequence default, Turn alternative); From/To number inputs bounded by what the stream actually contains; actor multi-select fed from `events._knownActors`; area select fed from the areas present in the stream; format select; destination (Save file | Copy); an "ignore stream filters" checkbox; and a live summary line (for example "ticks 12-340 | actor: Lyrie | area: Goblin Camp | 412 events | LLM filter off") that re-renders on every control change. The summary is what makes "what am I exporting" answerable before clicking.

Filenames carry unit, range and format: `<scenario>_<unit>_<from>-<to>_event_log_<ts>.{md,txt,json,jsonl}`.

## Steps to verify

Live browser on port 4444 (never headless - a unit test proves the renderer, only the browser proves the wiring). Load a scenario that has a run in the stream.

1. Open the range button.
   - expected: the modal shows a unit selector defaulting to Tick sequence, from/to bounded by the stream's own contents, and a summary line naming the active filters and the event count.
   - observed: LIVE (playwright, localhost:4444). Modal opens from the ⏩ button; unit default `tick`; to-input placeholder bounded to the stream's max (5 on the persisted run); summary read `ticks 0–5 | all actors | all areas | 69 events | markdown | filters applied`. Controls present: Unit, Range, Actors (multi, from the roster), Area, Format, Destination, Ignore-filters.
2. Export ticks 12-340 as JSONL, save to file, then query it with jq (count events per actor; select one actor's actions).
   - expected: one JSON object per line; every `seq` inside 12-340; every row carries actor/type/text; the jq queries return correct counts.
   - observed: PARTIAL. Unit test pins one-object-per-line, metadata rows excluded, and the record fields. Live: rendering the persisted run to JSONL produced 69 lines, all `JSON.parse` clean; JSON envelope `schema:1`, `counts.events:69`. NOT demonstrated: a fresh 12–340 tick range over a multi-actor run — the persisted stream held no ticked events in that band.
3. Set the stream toolbar's actor filter to one character, export as JSON.
   - expected: the envelope's `filters` block names the actor filter; every event's `actor` matches; the summary said so before the export.
   - observed: PARTIAL. `applyScope` actor filter is unit-tested; the actor multi-select populates from `events._knownActors` (live: `World`, `sammy lopez`). Not exercised against a multi-actor ticked run.
4. Tick "ignore stream filters", export as JSON.
   - expected: rows hidden by the kind chips are present; `filters.ignored` is true.
   - observed: LIVE. Summary flips to `filters IGNORED` on the checkbox; the projection's `ignoreFilters` path is unit-tested (a `display:none` row is skipped by default, included when set).
5. Export the same range as Markdown and as Plain.
   - expected: same shape as today's exports (turn headings, one bullet per event, raw-LLM `<details>` payload blocks) - no regression in the existing formats.
   - observed: LIVE renderers + unit tests. Markdown emits one `## Turn` heading per turn, one `- ` bullet per event, and a `<details>` block for a raw-LLM payload. The persisted stream had no turn cards, so 5b was demonstrated via an injected card.
5a. With an area filter active in the stream toolbar, export as Markdown, then reload the page and export again.
   - expected: the scope message appears as its own text (`📌 Scoped to: <area>`) with no `×` glued on, and no `⏭ up next:` bullet in either file. (Today: `data/exports/world_template_tick_613_event_log_2026-09-05T02-35-04.md:8` reads `- 📌 Scoped to: Weeping Willow Hollow×`, and the queue strip survives reload as a persisted child.)
   - observed: LIVE (injected banner into the live DOM). Projection returned `📌 Scoped to: Weeping Willow Hollow`, `×` present: false; renderer emitted no `⏭ up next:` bullet and skips `.turn-queue-strip`/`.timeline-scrubber`.
5b. Read any turn heading in the Markdown export.
   - expected: it ends with the game time, not a stray bracket. (Today all 14 headings in that same export end `08:15 🌑]` - the time regex's `[^)]*` swallows the label's closing `]`.)
   - observed: LIVE (injected turn card). Heading rendered `## Turn 5 — Lyrie · 08:15 · Day 3, Month 1, Year 1`; no trailing `]`. Unit test pins the same. Both `world-export.ts` heading regexes were also fixed to `[^\]|)]*`.
6. Use the file button and the clipboard button.
   - expected: both open the modal pre-set to the whole range with their destination; the resulting file and clipboard content match what those buttons produced before the change.
   - observed: LIVE. 📥 opens the modal with destination `file`; 📋 opens it with destination `clipboard`. The `WorldExport.*` surface and the three inline `onclick` handlers are unchanged (delegating stubs).
7. Run the gates: `python tools/ts_convert.py check` and `python tools/js_module_index.py --check`.
   - expected: green.
   - observed: both green. `ts_convert.py check` = build:ts / typecheck / lint / module:check / unit / header survival / window guards all ok; `js_module_index.py --check` = `Contract check OK (172 known-uncovered, 0 known-bad-@docs, no new)`. Unit: 682 passed, 0 failed.

## Acceptance

- JSON and JSONL exports exist and are queryable with jq without the app running.
- One modal owns range, scope, format and destination; the three header buttons are presets into it, not three implementations.
- The range unit is the tick sequence by default; turn remains selectable; the summary states the unit and the bounds.
- Stream filters are respected by default, named in the summary line, and overridable via the escape hatch.
- Markdown and plain output are unchanged in shape - the existing formats do not regress. Two defects the same walk already has are fixed here because the projection replaces it: the `textContent` fallback gluing a clear affordance's `×` onto the scope message, and the stray `]` on every turn heading.
- `world-export.ts` stays under the 600-line rule via the extracted module, and the `WorldExport.*` surface plus the three inline `onclick` handlers are unchanged.
- Gates green: `python tools/ts_convert.py check`, `python tools/js_module_index.py --check`.
- After live verification, `docs/virtualWorld/UI & Settings/Event Log Export.md` documents the formats, the event record shape, and the modal controls.

## Files

- `static/js/ui/event-log-export.ts` (new; emits the sibling `.js` via `npm run build:ts`)
- `static/js/ui/world-export.ts` (delegates the three entry points; the duplicated walks move out)
- `templates/index.html` (script tag for the new module; button titles)
- `docs/virtualWorld/UI & Settings/Event Log Export.md` (after verification)
