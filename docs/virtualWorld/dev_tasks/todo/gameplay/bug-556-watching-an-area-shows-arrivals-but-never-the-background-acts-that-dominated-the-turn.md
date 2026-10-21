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

## Reconciliation (2026-10-20) - STILL_VALID, re-measured

**Verdict: STILL_VALID.** The area ledger is still fed only by `turn_events`; the background acts are still only in `lived_log`.

**Re-measured 2026-10-20.**
- `static/js/inspector/area-view.ts:78` - still renders exactly one store: `const roomEvents = events.getAreaEvents(name);` (the `📜 Area Event Log` section at lines 117-136). No lived-log merge was added.
- `engine/lived_log.py:75-90` - `_tap` is still the single fan-out point and still fans out only to `engine.soak_telemetry.active_recorder`. The area ledger is still not among its targets.
- `engine/logging_events.py:68-117` - `record_turn_event` still appends to `self.turn_events` and still prunes to the current turn (`_MAX_TURN_EVENTS = 2000`, line 21); a world advance still never calls `clear_turn_events`.

**Counts (the four checks from the repo's "never infer runtime behaviour from existence" rule).**
1. **Is anything calling it?** `grep -c "record_turn_event" engine/background_simulation.py engine/background_plans.py` → 0 in both. The background tier still never writes to the witness ledger. Total `record_turn_event` call sites across `engine/`: 52, all in attended-action modules (`movement.py`, `items/*`, `speech.py`, `npc_behaviors.py`, `activities.py`, `skills.py`, `combat.py`, `crafting.py`, `grapple.py`, `equipment.py`, `lifecycle.py`, `soak.py`, `toggleable_items.py`, `background_social.py`).
2. **Is it reading the right object?** `area-view.ts:78` reads `events.getAreaEvents(name)`, which `world-state.ts:66-93` fills from `state.turn_events` plus the client's own `logAreaEvent` calls. `lived_log` is not in that path.
3. **Is any data authored that exercises it?** The card's own measurement (924 `turn_events` vs 577 `lived_log` entries, `act 352` / `need 21`) still stands as the ratio; nothing newer has added authored background acts to the ledger.
4. **Does the guard's signature match?** `_tap(character, tick, kind, what, why, area)` (`lived_log.py:75`) takes the full decision tuple; nothing on the area-log side reads that shape.

**Newer work checked.** `git log --oneline -10 -- engine/lived_log.py engine/logging_events.py engine/background_simulation.py engine/background_plans.py static/js/inspector/area-view.ts` returns `bbd4fc9f`, `8a1f0143`, `cb297187`, `0a697ef7`, `948b6a74`, `709331f7`, `b0e6cf5d`, `476734fa`, `8bdfe970`, `fb82e36b` - all older than the card's 2026-10-18 filing. The related cards `task-861` (streaming per-tick deltas) and `task-862` (no surface reads a character lived log) are both still `review`/`todo` and were re-read: neither implements the area-ledger projection the card asks for.

**Cited line drift.** `world-state.ts:66-93` is still correct. `area-view.ts:78` is still correct. `logging_events.py:104-117` is now `:104-117` (unchanged). `lived_log.py:75-97` is now `:75-90` for `_tap` itself (the function body shrank when the soak-telemetry import was moved inside the try); the card's `_tap` reference is still to the right function. `movement.py:770-775` has drifted - the shared traversal path now records at `movement.py:784` and `:789`. Corrected above.

**Status:** left in `todo`. The card's `How` still describes the two viable designs and the single-store-per-concept constraint; neither has been implemented.
