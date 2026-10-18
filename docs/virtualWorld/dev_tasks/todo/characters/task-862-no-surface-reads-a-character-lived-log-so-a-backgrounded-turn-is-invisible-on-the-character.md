---
type: task
status: todo
area: characters
priority: medium
horizon: now
effort: M
wiki: "[[Background Simulation|Background Simulation]]"
related: [task-861]
---

# task-862: No surface reads a character lived_log, so a backgrounded turn is invisible on the character

**Filed:** 2026-10-18
**Related:** task-861

<!-- deps:start -->
**Related:** [[task-861-world-advance-should-stream-a-per-tick-delta-so-the-event-stream-fills-while-the-request-runs]]
<!-- deps:end -->

## What

Give a character a surface that shows what they actually did, tick by tick. The background tier already records every decision to `player.lived_log` with `{tick, kind, what, why, area}`, and `GET /api/state` already ships it, but no UI reads the field: clicking a character shows memories, not the record of their turns.

## Why

Measured 2026-10-17 on the live :4444 world: the state payload carries `lived_log` for 27 characters, 577 entries in total, kinds `act 352, move 153, need 21, traversal 14, relationship 13, social 10, threat 8, death 2, plan 2, pursuit 2`. Sample rows: `Gribba act Hygiene fell to 50 why=needs:hygiene area=Chief's Pit`, `Croak-Mother act went to sleep why=needs:energy`, `Belne death died of old age (90) area=Raven River`. Grepping `lived_log` across `static/js` finds only `soak/soak-ui.ts` and `soak/soak-api.ts`, and those read soak telemetry and say in comments that the telemetry view is deliberately not the lived log. The only path from lived_log to the UI today is the indirect one: `tick_manager.py:1189-1197` calls `lived_log_memory.bridge_all` each turn, which phrases only some kinds into memories, so routine work leaves no visible trace at all. `lived_log.py:28-31` also records that the store is now unbounded (`MAX_ENTRIES = None`), which is why it belongs behind a scoped, paginated surface rather than a dump.

## How

Render the existing field, do not invent a new one. Add a history section to the character's Mind panel (or a tab beside Memories in the agent view) that reads `worldState.players[name].lived_log`, newest first, showing `what`, the `why` reason tag, `area` and the game clock for the tick, with the `kind` as a chip so needs-driven rows are distinguishable from planned ones. Group consecutive identical `kind` + `why` runs the way `lived_log.rollup` already does, and cap the rendered window rather than the store. Read-only: no writes back through this surface, so the lived log keeps exactly one writer per call site.

## Browser UI and intended live verification

Intended UI home: the character inspector, on the Mind panel, reached by clicking a character. Current availability: no section renders `lived_log`; the panel shows memories, which only cover the kinds the bridge phrases. Live path: click a backgrounded character after a world advance and read off what they did during the span.

## Steps to verify

1. After a 60-minute Advance World, open a character who moved during the span and read the new history section.
   - expected: the section lists their `lived_log` rows in tick order with what / why / area, matching the entries in the state payload.
   - observed: TODO
2. Confirm no second store was created: grep `lived_log` in `static/js` should now show the history surface as a reader, and the engine writers must be unchanged.
   - expected: one source of truth, one new reader.
   - observed: TODO

## Acceptance

- [ ] A character's panel shows their own `lived_log` entries, including needs-driven acts, not only bridged memories.
- [ ] The surface is read-only over the existing field and scoped (windowed), because the store is unbounded.
- [ ] `why` reason tags and `area` are shown, so a background decision stays explainable in the UI as it already is in the data.

## Files

- `static/js/inspector/agent-view.ts or the Mind panel module (new history section)`
- `static/js/types/globals.d.ts if a new accessor is published`
- `engine/lived_log.py (reference only: the store this renders)`
