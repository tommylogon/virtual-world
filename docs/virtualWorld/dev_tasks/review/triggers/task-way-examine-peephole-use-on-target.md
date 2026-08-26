---
group: Triggers
---

# Way & Area Triggers: examine, peephole, use-on target, area on_enter/on_examine

**Filed**: 2026-08-09  
**Priority**: Medium  
**Status**: In Review — implemented 2026-08-09, 6 new tests pass, full suite 779 passed (clean).

---

## Summary

Ways (doors) previously fired **only** `on_open`/`on_close`/`on_enter`; areas fired nothing. Gaps closed:

1. **Ways now fire `on_examine`** — examining a door (via its exit direction) runs the way's `on_examine` triggers.
2. **Peephole / see-through** — a **closed** way with `see_through` + `visible_in_direction` on the area→way edge appends "Through it you can see: {view}" on examine.
3. **use-on target fallback** — when an item is used on a way (`use rock on door`) and the *source* item's `on_use_on` produces no output, the **target way's `on_use`** fires.
4. **Areas now fire `on_examine`** — "examine the room"/"examine here" resolves the current area, describes it (description + non-normal state), and runs its `on_examine` triggers. Matches by name/id or the phrases room/area/here/surroundings; falls through to items when no area matches.
5. **Areas now fire `on_enter`** — moving into an area runs its `on_enter` triggers (alongside the door's existing on_enter).

## The semantics (worth pinning down — it bit us)

- **`on_use_on` is source-only**: "use SOURCE on TARGET" — the source item fires `on_use_on`; ways/areas/characters can be *targets*, never sources. "Use door 1 on Mike" is not a thing.
- **The target being acted on fires its `on_use`.** This matches the pre-existing item-target fallback in `use_item_on` (`matched_item` → `use_item` → `on_use`). My first pass wired the way's `on_use_on` as the fallback — wrong, and caught in review: `on_use_on` on the target would imply the target is the *source* of another use-on. The way's own `on_use` ("the door is being used") is the correct target-side event.
- **Source wins**: if the source item's `on_use_on` produces output, it returns early and the target's `on_use` never fires (keycard pattern keeps working).
- "Use door" alone (no item) is `on_use` (toggle/activate) — not wired for ways yet, separate concern.
- **Area `on_enter` outputs go to the log** (like the door's on_enter), not the move result string — matched existing behavior.

## Trigger matrix (agreed design)

| Trigger | item | way | area | character |
|---|---|---|---|---|
| on_examine | ✅ | ✅ (added) | ✅ (added) | ✅ |
| on_use / on_use_on | ✅ | ⚠️ use-on target only | ❌ | ❌ |
| on_open / on_close | ✅ (containers) | ✅ | ❌ | ❌ |
| on_take / on_drop / on_equip / on_unequip | ✅ | ❌ | ❌ | ❌ |
| on_tick / on_state_enter / on_state_exit | ✅ | ✅ | ❌ | ❌ |
| on_enter | ❌ | ✅ | ✅ (added) | ❌ |
| on_eat / on_drink / on_read / on_light | ✅ | ❌ | ❌ | ❌ |

Not implementing "all trigger types on all entity types" — verbs that don't make sense for a node type are excluded (a door can't be taken/eaten/equipped).

## Also fixed: state_equals UI redundancy

The trigger editor showed the generic **Value** field *and* the dedicated **State** field for `state_equals`, plus the generic **Target (blank = self)** *and* the dedicated **Target Node** — but collection only read the dedicated ones (`cond-node`/`cond-state`). Removed `state_equals` from both generic field lists so the row shows exactly: Target Node + State.

## Tests

`tests/test_trigger_system.py::TestWayTriggerFiring` (new, 6):
- `test_way_on_examine_fires` — door examine runs its on_examine trigger.
- `test_way_on_examine_peephole` — closed see_through door shows the view + locked state.
- `test_way_on_use_fires_when_item_silent` — passive item on door fires the door's `on_use`.
- `test_way_on_use_not_fired_when_item_has_on_use_on` — source on_use_on wins, target on_use does not double-fire.
- `test_area_on_examine_fires` — examining the current area runs its on_examine triggers (with description).
- `test_area_on_enter_fires` — moving into an area runs its on_enter triggers (logged).

## Files Changed

- `engine/item_actions.py` — way-examine trigger execution + peephole glimpse; way-side use-on fallback fires `on_use` (was `on_use_on`); area-examine path with on_examine triggers
- `engine/movement.py` — area `on_enter` trigger execution on arrival
- `static/js/shared/trigger-editor.js` — `state_equals` no longer shows the generic Value / Target fields
- `tests/test_trigger_system.py` — `TestWayTriggerFiring`
