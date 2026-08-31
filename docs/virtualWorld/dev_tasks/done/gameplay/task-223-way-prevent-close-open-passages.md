---
group: Gameplay
wiki: "[[dev_tasks/level-design-workflow]]"
---

# Way State Guards — prevent_close for Pits, Ladders, Open Shafts

**Filed**: 2026-08-13  
**Priority**: Low  
**Status**: Done — implemented 2026-08-16. Engine guard in `engine/movement.py` (`_open_passage_block`, both `toggle_way` + `toggle_way_by_id`): jump/climb/crawl ways are uncloseable/unopenable by **characters**; `prevent_close` flag pins any way open. The inspector is a **designer surface and stays free** — its Open/Close buttons (`toggleDoorState`) now PATCH the way node directly (like the way editor's State dropdown), so designers can set any state; only character/agent commands are guarded. Way editor got a **Prevent closing** checkbox (persisted in way node + library sync). Triggers (`set_state`-style effects) write `current_state` directly and still work. Tests: `tests/test_movement.py::TestOpenPassageGuards` (7 tests); full suite 951 passed. Moved to review/.

---

## Problem

Any way including open jump pits and ladders can be closed via area inspector **Open/Close** buttons (`toggleDoorState`) or triggers that set `current_state: closed`. For labs Task 18 jump pit and ladder shaft, closing would nonsensically "shut" an open hole or climbable ladder.

Nothing in the engine prevents this today. but i do want to allow triggers to still open or close ways.

## Goal

If a way has  traversal type of jump, climb or crawl, do not allow charaters to close or open those by doing open "way name" or close "wayname", only allow via triggers.
- Blocks player/agent `close` actions on that way


## Use cases

| Way type  |
|----------|---------------------|
| Jump pit (`requires: jump`) |
| Ladder (`requires: climb`)  |
| Normal door | false |



## Implementation

- `engine/movement.py` — refuse character open/close on jump/climb/crawl ways and `prevent_close` flags (`_open_passage_block` in `toggle_way` + `toggle_way_by_id`)
- `static/js/main.js` — `toggleDoorState` (inspector Open/Close buttons) uses the direct node PATCH instead of the action route, keeping the inspector fully authoring-capable
- `static/js/inspector/way-view.js` — **☐ Prevent closing (open passage)** checkbox (passage tab), saved to node + library sync
- Way node properties + serialization (`prevent_close` through save/refresh/library)

## Verification

- [x] Jump way: character `close`/`open` refused, state unchanged
- [x] Normal door: still closable/openable by characters
- [x] Inspector can still set any way state (designer freedom — PATCH path)
- [x] `prevent_close` flag blocks character close, allows character open
- [x] Agent `close` on a guarded way fails gracefully (same engine path as human)

## Related

- [[todo/ui/task-220-unified-way-editor|task-220]]
- User way templates — set default for pit/ladder templates
