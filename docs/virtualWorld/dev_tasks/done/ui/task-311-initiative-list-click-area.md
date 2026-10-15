---
area: ui
type: task
status: done
priority: medium
---

# Click Area Name in Initiative List

**Filed**: 2026-08-19
**Priority**: Low
**Status**: In Review — implemented 2026-08-19 (clickable area in agent list)

---

## Idea

In the initiative list, allow clicking the area name next to each agent to navigate/select that agent's room.

## Implemented

- `static/js/ui-controller.js` — the existing `agent-location` span is now clickable (dotted underline, stopPropagation so it doesn't select the agent row) and calls `graphManager._selectRoom(areaName)` to open the area in the inspector + focus it in the graph.

**Verified**: `node --check` clean; full suite 980 passed.

## Notes

- Trivial UX win: makes the area name in the initiative list a clickable link that selects the room in the graph/editor.
- Small, self-contained.

## Related

- `developer ideas.md` line 18
- Initiative/turn UI (`static/js/`)

## What

TODO

## Why

TODO

## How

TODO

## Steps to verify

- expected: the area name next to an agent in the initiative list is clickable and selects the room.
- observed (2026-10-10 live): 27 .agent-location spans, cursor:pointer + underline; clicking 'Cooking Area' opened the Area inspector.

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Left panel → Agents list → click the agent's location label.

Current availability: The location text is recorded as a clickable
`agent-location` span that calls `_selectRoom()` and stops row-click
propagation. The card records a live click on Cooking Area that opened its Area
Inspector.

Live steps when available:
1. In the Agents list, click the location label `Cooking Area` beside an
   agent; observe the graph focus and right Inspector.
   - expected: Cooking Area is selected in the graph and its Area Inspector
     opens; the agent row itself does not select a different character.
2. Click the location label again after selecting another agent row.
   - expected: the room navigation follows the clicked label and does not
     consume the agent-row click behavior.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
