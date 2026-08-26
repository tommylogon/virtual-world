---
group: UI
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
