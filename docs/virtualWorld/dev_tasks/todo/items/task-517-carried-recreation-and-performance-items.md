---
type: task
status: todo
area: items
priority: medium
---

# task-517: Carried recreation and performance items

**Filed:** 2026-09-24
**Related:** task-425, task-136, task-409

## Goal

Let carried entertainment items — Rikka's juggling stones, string puppet, cups,
little drum — restore Entertainment and be usable by background NPCs, beyond
today's area-fixture-only recreation.

## Context

- Recreation is area-fixture only: `RECREATION_TAGS = ("recreation",)`
  (`engine/background_simulation.py:73`) and `_recreate` (line 486) looks for a
  fixture via `_service_here`, taking the amount from the fixture's
  `entertainment` property (default 15).
- Entertainment is otherwise paid by novelty (task-136) and by
  `joke`/`tease`/`flirt` (`engine/background_social.py:114-154`); plain
  conversation is Social, not Entertainment.
- A settled goblin's Entertainment otherwise decays to 0 (comment at
  `engine/background_simulation.py:489-492`).
- Items already support `actions`/`use`, `uses` and `action_costs` (see the
  flashlight/EMF reader in `data/library/characters/elena vance.json`), but
  nothing routes a `use` to `adjust_vital Entertainment`, and the background
  sim cannot pick a *carried* item.

## Proposal

- Author entertainment items with tag `recreation` and a `use` effect/trigger
  `adjust_vital Entertainment` (amount plus finite `uses` where appropriate) so
  foreground use works.
- Extend `_recreate` to fall back to a carried `recreation` item when no area
  fixture exists, debiting uses/Energy and keeping the need-gate anti-spam.
- Decide whether "distraction" (a performance pulling attention) is a real
  mechanic or narration only; if a mechanic, relate it to combat/interrupts.

## Acceptance

- Using a carried recreation item raises Entertainment (foreground), with uses
  and anti-spam behaving.
- A background NPC with a recreation item but no fixture can recreate (tested)
  and does not spam it.
- The fixture path is unchanged and soak/determinism tests are unaffected beyond
  the expected Entertainment rise.
- Rikka's kit is authored on the model.

## Non-goals

- A full performance/skill minigame.
- Novelty/discovery Entertainment (task-136).
