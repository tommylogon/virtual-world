---
type: task
status: cancelled
area: ui
priority: low
---

# task-415: Long-horizon observer mode

**Filed:** 2026-09-19  
**Dropped:** 2026-09-19 — deferred for now; revisit once 411/412/414 exist.  
**Depends on:** task-340 (event stream v2), task-333 (human turn panel),
task-414 (batch advance), task-411 (attention tiers), task-412
(promotion/demotion).  
**Note:** ties existing UI work together; does not replace those tasks.

## Goal

Let the user **watch** a long-running world, **follow** a character, and **drop
in** to interact — the "experience it, don't just measure it" goal.
example if tha tof humanoid agents https://github.com/humanoidagents/humanoidagents
## Changes

1. **Observer view.** Live world clock, notable events drawn from the trace,
   alive/dead counts and key vitals, and who is currently attended (task-411).
2. **Follow a character.** Pin a character as an anchor (promote via task-412);
   show their recent trace and memories as the world runs.
3. **Drop in.** Switch from observer to embodied human for the pinned character
   without breaking a running batch; then return to observer (demote).
4. **Honest background display.** Background spans are shown from structured
   trace entries ("slept 8h, drank, travelled to …"), never prose the engine
   invented.

## Acceptance

- Watch a week-scale run with the clock and notable events streaming.
- Follow → drop in → return works without duplicating actions or memories.
- Background facts displayed come only from trace entries (no fabricated prose).
- The view stays responsive while a server-side batch is running.

## Non-goals

- A new rendering engine.
- Editing the world from observer mode.

## Verification

- A browser/manual pass over a long run: watch, follow, drop in, return.
- Assert the displayed background facts match trace entries for the character.
