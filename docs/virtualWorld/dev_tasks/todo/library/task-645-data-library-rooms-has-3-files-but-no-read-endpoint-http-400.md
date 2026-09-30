---
type: task
status: todo
area: library
priority: low
---

# task-645: data/library/rooms has 3 files but no read endpoint (HTTP 400)

**Filed:** 2026-09-30
**Related:** 

## Goal

GET /api/library/rooms returns 400 while data/library/rooms/ contains 3 json files, so the room registry has no route to read it. Found while retracting task-620, which had wrongly claimed structures was unreachable.

## Acceptance

- TODO

## Correction 2026-09-30 — not a missing route; the directory is legacy saves

The filed claim was "`data/library/rooms` has 3 files but no read endpoint
(HTTP 400), so the room registry has no route to read it." The 400 is real and
the cause is exactly as filed -- `REGISTRY_TYPES` in `routes/library_ops.py:17`
is

    ['items', 'characters', 'areas', 'ways', 'traits', 'conditions',
     'behaviours', 'tags', 'triggers', 'structures']

and `rooms` is not in it. **But `rooms` was never meant to be in it, and adding
it would be a bug.**

`data/library/rooms/` does not hold a room registry. It holds **legacy save
files from an older save format that lived at that path**:

| file | size | top-level keys | modified |
|---|---|---|---|
| `mansion.json` | 425,981 | `current_area, players_in_area, players, active_player, game_time, time_ticks, time_per_tick_minutes, clock_start_hour` | 2026-08-26 |
| `world_template.json` | 98,822 | same shape | 2026-08-31 |
| `fighting_pit.json` | 1,079 | `name, description, environment` | 2026-08-26 |

Those are **runtime state payloads**, not authored registry entries -- they carry
`active_player` and the game clock. And the directory is known to code by path:

    migrate_legacy_triggers.py:224
      help="Migrate mansion.json, mansion2.json, and library/rooms/mansion.json"

So adding `rooms` to `REGISTRY_TYPES` would publish **526KB of live save-state as
authored library content**, which the library browser and the linters would then
treat as registry entries. That is the opposite of the fix.

### The real, smaller issue this surfaced

**Runtime saves are sitting inside the authored-content tree.** `data/library/`
is the library, and anything that walks it -- `load_registry`, the lint, the
library browser -- will encounter these three files as though they were content.
They are weeks stale, so nothing reads them, which means they are also invisible:
nothing reports them, nothing cleans them, and the 400 is the only signal they
produce at all.

Two things worth deciding, neither of which is "add the route":

1. Should the migration consume and remove them (they are what the script reads),
   or is keeping them deliberate as a backup?
2. If they stay, should `data/library/` exclude non-registry subdirectories, so a
   library sweep cannot mistake a save for content in the first place?

`fighting_pit.json` is a third shape again (`name, description, environment`) and
does not belong with the other two -- worth working out which of the three is
still needed before touching any of them.