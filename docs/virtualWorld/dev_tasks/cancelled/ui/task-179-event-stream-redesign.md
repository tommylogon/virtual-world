---
group: UI
---

# Event Stream Redesign — Turn Cards, Structured Events, LLM Chips

**Filed**: 2026-08-05
**Priority**: Medium
**Status**: Cancelled — superseded by task-340 (Event Stream v2)

## Why cancelled

This design doc (plus `docs/design/event-stream-demo.html`) was the precursor to
task-340, which implemented the full structured timeline UI on 2026-08-24:
turn cards, structured event rows, collapsed LLM chips, filters, persistence
cap, scrubber, raw-LLM inspection, story mode. Everything this task envisioned
is live under task-340 — see `review/ui/task-340-event-stream-v2.md`.

Kept here for the callsite audit table (234 `events.log()` callsites across 27
files) which task-340 used as its contracting scope.
