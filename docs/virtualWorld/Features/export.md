---
type: feature
feature_id: 65
status: wired
section: in-editor
tags: [status/wired, surface/in-editor, system/ui]
---

# Export

**What you can do:** Graph export, play-session log export — the event log to Markdown, plain text, JSON or JSONL, one run-range / actor / area at a time

## How it works

- [[Event Log Export]]

## Where it lives

- `static/js/ui/event-log-export.ts` — the event-log projection, the four renderers and the export modal
- `static/js/ui/world-export.ts` — `saveFileWithDialog` and the three header-button delegators
- `static/js/event-stream.ts` — `_nextLineLabel` stamps `data-seq` on each emitted row
- `static/js/graph/graph-export.ts` — graph export (the other half of this feature)

## Connected

- Feature Map: [[Feature Map|row 65]] (In the editor)
- Sibling features: [[graph-canvas]], [[map-layout]], [[levels-layout]], [[worldpainter]], [[grid-to-graph]], [[scopes]]
- All features: [[Features Overview]]

> [!note] Status — `wired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-05. This page is an entry point; the
> deep documentation is linked under **How it works**.
