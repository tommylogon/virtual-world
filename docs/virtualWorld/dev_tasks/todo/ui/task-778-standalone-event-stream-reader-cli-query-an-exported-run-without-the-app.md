---
type: task
status: todo
area: ui
priority: low
related: [task-347, task-777]
blocked_by: [task-777]
---

# task-778: Standalone event-stream reader CLI: query an exported run without the app

**Filed:** 2026-10-11
**Related:** task-347, task-777

<!-- deps:start -->
**Blocked by:** [[task-777-event-stream-export-json-jsonl-formats-and-one-consolidated-export-modal-tick-sequence-range-actor-area-scope-filter-honesty]]
**Related:** [[task-347-export-log-lint-guards]], [[task-777-event-stream-export-json-jsonl-formats-and-one-consolidated-export-modal-tick-sequence-range-actor-area-scope-filter-honesty]]
<!-- deps:end -->

## What

A standalone node CLI that reads an exported event-stream JSONL/JSON file and answers "what happened during this run" without the app or a server: filter by actor, area, event type, and tick-sequence range; print a timeline, per-actor summaries, or raw matching events. Precedent: `tools/log_lint.cjs`, which already reads export logs as text with no server.

Depends on task-777's event record shape (`{ seq, tick, time, turn, actor, area, type, text, outcome?, payload? }`) - the reader consumes that schema, so it cannot land first.

## Why

Today the only way to read a run back is to open the app and scroll, or grep Markdown by hand. task-347's linter proves the value of a text-only reader over exports; a structured reader turns the same exports into queries ("every failed action by Lyrie in the goblin camp", "what happened between ticks 200 and 260").

## How

New `tools/stream_read.cjs` (or similar) following `tools/log_lint.cjs` conventions: plain node, no dependencies, `--json` output option, non-zero exit on usage/IO error. Flags for actor, area, type, from/to (tick sequence), plus output modes (timeline, per-actor summary, raw events). Wire it into the release checklist next to `npm run loglint` if it proves useful.

## Steps to verify

1. Run the reader over a JSONL export produced by task-777 from a real session.
   - expected: it prints a correct timeline and the per-actor counts match a jq count over the same file.
   - observed: ___
2. Filter by one actor and a tick range.
   - expected: only that actor's events inside the range print.
   - observed: ___

## Acceptance

- Reads a task-777 JSONL or JSON export with no server and no app.
- Actor, area, type and tick-sequence range filters work and agree with jq over the same file.
- Follows the log_lint.cjs CLI conventions (flags, --json, exit codes).

## Files

- `tools/stream_read.cjs` (new)
- `docs/virtualWorld/UI & Settings/Event Log Export.md` (reader usage, after verification)

## Browser UI and intended live verification

Intended UI home: Not applicable — the deliverable is a standalone Node CLI that reads an exported JSON/JSONL file without the app or browser.

Current availability: The event-record format is owned by task-777; this reader depends on task-777 and is not claimed as implemented.

Live steps when available: Not applicable.

Why no browser UI: The acceptance explicitly requires querying an exported run with no server and no app; a browser step would add a dependency the tool is meant to remove.

Alternative verification steps:
1. Export a real task-777 JSONL run, then run `node tools/stream_read.cjs <export.jsonl> --from 0 --to 17 --json` with the app stopped.
   - expected: the command exits successfully and emits only JSON for events in tick-sequence range 0–17.
2. Run the CLI's per-actor summary on that same file and compare its counts with `jq -s 'group_by(.actor) | map({actor:.[0].actor,count:length})' <export.jsonl>`.
   - expected: each actor count matches the independent `jq` result.
3. Filter by one actor and area, then compare the output with a direct `jq` selection on the same fields.
   - expected: only records matching actor, area, type, and sequence range appear; invalid file/flag input returns a non-zero exit code.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
