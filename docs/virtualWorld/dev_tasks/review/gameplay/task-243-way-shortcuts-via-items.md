# Task-243: Way Shortcuts Revealed by Having an Item
**Status**: In Review — implemented 2026-08-31 (per Tommy: gate approach — "a trigger that on go checks has_item bike"). New `requires_item` way property: name/id ("bike") or tag gate ("tag:fly"), enforced in the movement passage gate (engine/movement.py) — visible-but-blocked without the gear, usable with it. Prompt exit lines show "(needs: bike)". tests/test_way_gates.py (5).

**Audit 2026-08-31** — NOT IMPLEMENTED. Touches the central way-visibility model (way_visible_to, build_exits_for_area, movement gate) every prompt/look/scene surface reads. **Needs a design decision** (reveal-as-exit vs traversable-only; item source) before code.


**Status:** In backlog — filed 2026-08-16 from developer ideas backlog.
**Source:** `dev_tasks/developer ideas.md` (way shortcuts revealed by having item)

## Goal

A way can be gated so it is only known/revealed (shown as an exit / navigable) while a
character holds a specific item — e.g. a hidden passage or shortcut that appears in the
room's exit list only when you carry the key/map/token.

## Notes / open questions

- Model as an `unlocks`/`requires`-style edge plus item-presence condition on the way, or a
  trigger (`on_enter_area`) that toggles way visibility based on inventory.
- Reveal semantics: does the way appear in exits (visited, but not in "ways to go"), or
  only become traversable? Should holding the item re-route to a different destination.
- Interaction with existing `hidden` way state and `view_from_a`/`view_from_b`.