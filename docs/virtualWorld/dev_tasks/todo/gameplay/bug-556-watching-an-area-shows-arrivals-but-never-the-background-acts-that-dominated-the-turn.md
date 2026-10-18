---
type: bug
status: todo
area: gameplay
priority: medium
horizon: next
effort: M
wiki: "[[Background Simulation|Background Simulation]]"
related: [task-861, task-862]
---

# bug-556: Watching an area shows arrivals but never the background acts that dominated the turn

**Filed:** 2026-10-18
**Related:** task-861, task-862

<!-- deps:start -->
**Related:** [[task-861-world-advance-should-stream-a-per-tick-delta-so-the-event-stream-fills-while-the-request-runs]], [[task-862-no-surface-reads-a-character-lived-log-so-a-backgrounded-turn-is-invisible-on-the-character]]
<!-- deps:end -->

## What

Watching an area shows which characters arrived but never what they did there. The background tier writes movement to `turn_events` (so it reaches the Area Event Log) while its needs and acts go only to `lived_log` (which the area log never reads), so the witness view is half-fed by accident.

## Why

Measured 2026-10-17 on the live :4444 world after a 60-minute world advance: `turn_events` held 924 entries, actions `move 594, npc_behavior 216, speak 72, sleeping 25, activity_end 17`, of which 301 belong to the real cast (Rikka 54, Gribba 44, Zikka 26, Cullen Rutherford 25). The same span left 577 `lived_log` entries whose bulk is `act 352` and `need 21` rows like `relieved themselves improvisionally in Food Storage (needs:relieve:public)`, `washed in <area>`, `rested in <area>`. `area-view.ts:78` renders exactly one store, `events.getAreaEvents(name)`, which `world-state.ts:66-93` fills from `state.turn_events` plus the client's own `logAreaEvent` calls (`event-stream.ts:715-728`). Grepping the `record_turn_event` callers shows `background_simulation.py` and `background_plans.py` never call it; the movement rows arrive indirectly, through `movement.py:770-775` on the shared traversal path. So `lived_log.py:75-97` (`_tap`) is the one place a background decision is already fanned out to a second consumer, and the area ledger is not among its targets.

## How

Make the area ledger a deliberate projection rather than a side effect of the movement call sites. Either fan out from the single `lived_log.record` choke point to the turn-event buffer for the kinds an onlooker in that area could witness (act, move, need, death, social, threat - leaving plan and pursuit internal), reusing the `_tap` pattern so the ~20 call sites are not duplicated, or widen `getAreaEvents` to merge the same kinds from the area's characters' lived logs client-side. Pick one store per concept: `turn_events` is the per-turn witness ledger and `lived_log` stays the character's own record, so the projection must not become a third copy. Watch the buffer: `logging_events.py:104-117` prunes to the current turn and caps the list, and a world advance never calls `clear_turn_events`, so a busy span accumulates - the per-frame and per-area caps from task-861 apply here too.

## Browser UI and intended live verification

Intended UI home: the inspector's `📜 Area Event Log (who did what)` section on an area. Current availability: shows arrivals, speech and sleep, never the need-satisfaction acts that dominate a backgrounded character's turn. Live path: watch an area with characters in it, run an advance, and confirm the log says who ate, drank, washed and rested, not only who walked in.

## Steps to verify

1. Advance the world 60 minutes with characters in the Food Storage / Chief's Pit area, then open that area's inspector.
   - expected: the Area Event Log lists need-satisfaction acts for those characters, matching their `lived_log` rows for the same span.
   - observed: TODO
2. Check the ledger stays bounded: read `len(turn_events)` in the payload before and after a long advance.
   - expected: growth is capped by the existing prune and cap, and the state payload does not balloon.
   - observed: TODO

## Acceptance

- [ ] A witnessable background act reaches the area ledger through one documented projection, not a scattered new call site per action.
- [ ] Plan and pursuit rows stay out of the area ledger (they are internal to the character).
- [ ] The existing per-turn prune and cap still bound the buffer after a long advance.

## Files

- `engine/lived_log.py (_tap fan-out point) or engine/logging_events.py`
- `engine/background_simulation.py (the kinds it records)`
- `static/js/world-state.ts (_syncTurnEvents) if the merge happens client-side`
