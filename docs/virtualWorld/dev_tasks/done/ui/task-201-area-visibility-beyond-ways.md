---
area: ui
wiki: "[[dev_tasks/level-design-workflow]]"
type: task
status: done
priority: medium
---

# Area Visibility Beyond Ways (examine + observation prompt)

**Filed**: 2026-08-10  
**Priority**: Medium  
**Status**: In Review — implemented 2026-08-13; pytest `test_beyond_visibility.py` (7 passed); browser E2E pending

---

## Why

"From where you stand, the Upstairs Hall is visible beyond" currently lists little beyond auto env clues. There is no way to toggle whether characters/items in an area beyond a way appear in the narrative or agent prompt.

## How

- This is not just the examine view — it also applies to the **agent room context** (`buildRoomContext` exits block).
- The backend already has partial data (`see_through`, `area_description.py` visibility).
- Two parts:
  - (a) Per-direction visibility on the **area→way connection edge** (same place as `visible_in_direction`):
    - `allow_see_characters` — boolean; when true, list people in the **target** area on the exit line.
    - `visible_items` — **string array** (multiselect); only the chosen item names from the target area appear. Empty = no dynamic items (author opts in per item).
  - (b) Inject target-area highlights into the agent observation prompt when way is open / see-through.
- UI lives in way inspector **Connections** tab — one multiselect per direction (“From Kitchen → Living Room”), populated from items currently in the target area. Gating is backend.

### Data shape (area→way edge properties)

```json
{
  "direction": "stairs",
  "visible_in_direction": "The upstairs hallway beyond, with the master bedroom door…",
  "allow_see_characters": true,
  "visible_items": ["Grandfather Clock", "wooden chest"]
}
```

From area A looking toward B: read the A→way edge; target area = B. Only items whose **name** is in `visible_items` and that are present in B (direct, spatial, or on a surface in B) are listed. Hidden items never appear.

### Runtime rules

- Applies when way is **open**, or **closed + see_through** (peephole/glass).
- Dynamic highlights append to the exit line after env clues / `visible_in_direction` prose.
- `allow_see_characters` uses the same stranger/known naming as “People here”.
- If `visible_items` is missing or `[]`, no dynamic items — static `visible_in_direction` text still works.

## Agent Lens integration (task-219)

When implemented, task-201 controls must appear in **left-panel Agent Lens**:

- Toggle `see_through`, `allow_see_characters`, `visible_items` in **preview-only** mode
- Show whether target-area people/items would appear in exits/people blocks
- Live update when flags change in inspector

Do not build a separate preview surface — extend task-219 lens.

## Files

- `engine/area_description.py` — read `allow_see_characters` / `visible_items` from area→way edges
- `static/js/agent/prompt-builder/room-context.js` — inject target-area highlights into exits/people sections
- `static/js/inspector/way-view.js` (Connections tab) — character checkbox + item multiselect per direction
- `engine/serialization.py` — persist `visible_items` / `allow_see_characters` on connection edges
- `static/js/agent-lens.js` — preview toggles (depends on task-219)

## Related

- [[todo/ui/task-219-agent-lens-left-panel|task-219]]
- [[todo/ui/task-220-unified-way-editor|task-220]]
- [[dev_tasks/level-design-workflow|Level design workflow hub]]

## What

TODO

## Steps to verify

1. Run `python -m pytest tests/test_beyond_visibility.py` for the recorded
   backend visibility cases.
   - expected: open and see-through ways reveal only configured, present,
     non-hidden items and the requested target-area characters.
   - observed (2026-08-13): the card records 7 passing tests; browser E2E is
     still pending.
2. Follow the Connections and Agent Lens steps below in the browser after both
   UI pieces are available.
   - expected: the per-direction controls save on the source edge and the Lens
     preview matches the runtime visibility rules.
   - observed: not recorded; the card's own browser acceptance remains open.

## Acceptance

- [ ] TODO

## Browser UI and intended live verification

Intended UI home: Graph → select a way → Inspector → Connections; left-panel
Agent Lens → preview the source area's exits and people.

Current availability: The card records the backend visibility rules and agent
room-context work as implemented. Its own notes say the per-direction editor
controls and Lens preview toggles depend on task-219 and browser E2E is pending;
the `done` folder is not evidence those UI steps passed.

Live steps when available:
1. In a scratch scenario, select the Kitchen-to-Hall way and open Connections.
   Enable `allow_see_characters` for that direction and select one named item
   present in the Hall under `visible_items`; save the passage.
   - expected: the authored values belong to Kitchen → way, not the reverse
     edge, and the target item is selected by its name.
2. Open the Kitchen view in Agent Lens with the way open, then repeat with the
   way closed and `see_through` enabled; include an unselected item and a
   hidden item in the Hall as controls.
   - expected: Hall characters and only the selected present item appear in the
     prompt's exit view when visible; the unselected and hidden items never do.
3. Turn off `allow_see_characters`, clear `visible_items`, and refresh the
   preview without saving any further world edit.
   - expected: dynamic people/items disappear while static
     `visible_in_direction` prose remains.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
