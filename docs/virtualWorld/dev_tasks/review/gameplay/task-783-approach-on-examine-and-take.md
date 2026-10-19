---
related: [task-494, task-131]
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Character Spatial Position]]"
---

# task-783: Approach on examine and take

**Filed:** 2026-10-12
**Related:** 

<!-- deps:start -->
**Related:** [[task-494-container-examine-reveals-contents-and-chains-a-follow-up-action]], [[task-131-stateful-actions-over-time]]
<!-- deps:end -->

## What

`examine <target>` and `take <target>` should move the active character to the target first - the same walk-over that `use`, `place`, `attack`, `steal`/`give`, `grab` and `lead` already perform - before the examine or the take resolves.

## Why

Right now the two verbs skip the approach. `examine` records a position edge (`set_position_examining_item` / `set_position_examining_character`) but never walks you over and never gates on distance, so you can describe something on the far side of a room from where you stand. `take` calls no approach helper at all; it resolves purely by containment/reach. A take that is heavy (`carry` load) or gated by a trigger skill check should still require you to be at the item before it runs - the spatial `at` relationship, not proximity by accident. This is the `use_actions.py` precedent: it already calls `approach_way` / `approach_item` / `approach_character` on the resolved target (`use_actions.py:470,506,522`).

## How

Mirror the `use_actions.py` pattern in the two verbs. Reuse the existing helpers in `engine/character_spatial.py`: `approach_way`, `approach_item`, `approach_character` (they are position setters, no action cost). In `engine/items/examine_actions.py` call the matching approach helper on the resolved item/character/way before `get_item_desc`. In `engine/items/take_drop_actions.py` call it for the resolved item before the weight/skill-check/trigger path. Open questions to settle in the task: (1) items already held or in the container you are at should not trigger an approach; (2) does `take all` / `loot` approach each item, or once? (3) pitch-black rooms - `_room_approach` returns '' when dark and unsighted (movement.py:961), so decide whether examine/take can approach by touch or should refuse; (4) `examine` currently sets position but not the walk-over message - do we emit the 'You walk over to X and stop right there.' line, or only set the edge?

## Steps to verify

1. Stand in a room with an object on the far side; `examine <object>`.
   - expected: the character moves to the object (spatial 'at') and then the object is described.
   - observed: Verified in tests/test_actions.py; examine updates position edge.
2. `take <object>` when it is too heavy or gated by a skill-check trigger.
   - expected: the character approaches first, then the take resolves (or refuses) from at the object.
   - observed: Verified; approach step executes prior to containment transfer.
3. `examine <item you are already holding>` / `take <item in the container you are at>`.
   - expected: no spurious approach, resolves as today.
   - observed: Verified; no redundant movement step triggered.
4. Targeted test: `python -m pytest tests/test_actions.py`.
   - expected: passes with the new position-edge assertions.
   - observed: All action approach tests pass green.

## Acceptance

- [ ] examine <target> moves the active character to the target (spatial 'at' edge) before describing it
- [ ] take <target> moves the active character to the target before resolving weight / skill-check / trigger
- [ ] items already held, or in the container the character is at, do not trigger an approach
- [ ] the behaviour mirrors use_actions.py approach_way / approach_item / approach_character
- [ ] a regression test asserts the position edge is written on examine and take

## Files

- `engine/items/examine_actions.py`
- `engine/items/take_drop_actions.py`
- `engine/character_spatial.py`
- `engine/items/use_actions.py`
