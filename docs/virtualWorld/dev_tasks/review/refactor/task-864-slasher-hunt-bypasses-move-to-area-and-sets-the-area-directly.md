---
type: task
status: review
area: refactor
priority: medium
wiki: "[[Movement]]"
related: [task-775]
---

# task-864: Slasher hunt bypasses move_to_area and sets the area directly

**Filed:** 2026-10-18
**Related:** task-775

<!-- deps:start -->
**Related:** [[task-775-sibling-scope-traversal-border-seam-remap-and-footprint-placement]]
<!-- deps:end -->

## What

The slasher hunt moves a character by setting the area directly: `self.gs.name_matcher._set_player_area(slasher_name, target_area_node.name)` (`engine/npc_behaviors.py:800`), under the comment "bypass normal move logic for the AI". Every other controller moves through `movement.move_to_area`: human and LLM via `/api/action` (`routes/action_handlers.py:397`), simple NPC at `engine/npc_behaviors.py:566`, `595`, `645`, `673`, and backsim or timeskip via `traversal.hop` (`engine/traversal.py:271-284`). This one path skips the gates, the verb, and load-before-you-move.

## Why

One character, one movement (task-399:21-22). Setting the area directly means the slasher crosses a way that may be locked, blocked or verb-required, and because `ensure_destination_loaded` lives inside `move_to_area` (`engine/movement.py:645`), a slasher whose target is in an evicted scope can set `current_area` to an area that is not in the graph. The bypass is legacy: nothing requires it, and the simple-NPC wander path already shows the intended shape (save `active_player`, call `move_to_area`, restore).

## How

Replace the direct `_set_player_area` with the pattern the wander and flee paths use: save `gs.active_player`, set it to the slasher's name, call `gs.movement.move_to_area(direction)` inside a try/finally that restores it, and keep the `record_turn_event`. Preserve the deliberate slasher rule that it may force a closed way open: set that on the way node before the move, then cross through the normal seam. Keep the returned line intact unless the wording genuinely needs to change. Do not add a second mover; the seam is `move_to_area`.

## Browser UI and intended live verification

N/A - an engine refactor with no new surface. The observable path is a targeted test of the slasher hunt (`tests/test_npc_behaviors.py`), plus a live hunt in the game view if a slasher scenario is loaded.

## Steps to verify

1. A slasher hunting a target across a way.
   - expected: the slasher moves through `move_to_area`, with the same gates, verb and load-before-you-move as any other character.
   - observed: TODO
2. A slasher whose target is in an evicted scope.
   - expected: the destination scope loads on demand, or the move refuses cleanly; `current_area` is never an area absent from the graph.
   - observed: TODO
3. Grep for `_set_player_area` outside authoring, admin, teleport and grapple callers.
   - expected: no NPC movement path remains.
   - observed: TODO

## Acceptance

- [ ] No NPC movement path sets `current_area` by direct `_set_player_area`.
- [ ] The slasher moves through `move_to_area` like every other controller.
- [ ] A regression test proves a slasher's move respects a closed or locked way, or loads the destination.

## Files

- `engine/npc_behaviors.py`
- `engine/movement.py`
- `tests/test_npc_behaviors.py`

## Decision (2026-10-20)

`slasher_hunt` is unused dead code from an early horror prototype (0 runtime callers outside virtual_world_engine.py). Instead of merely fixing the mover to `move_to_area`, the slasher mechanic should be retired as a hardcoded Python method on `npc_behaviors` altogether. Hunting / stalking belongs in the declarative behavior / goal / pursuit system (`pursuit: hunt`, `behavior: stalk/hunt`) reading normal movement and combat contracts.

