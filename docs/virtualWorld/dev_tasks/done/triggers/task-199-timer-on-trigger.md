---
group: Trigger System
---

# First-Class Timer on Trigger

**Filed**: 2026-08-10
**Priority**: Low
**Status**: Todo

---

## Problem

Timing is currently hacked via a "timer item" pattern. There is no first-class way to express "this happens after N ticks" on a trigger.

## Design

- A workable timer-item workaround exists: on_tick reduces uses, then a conditional unlock fires when uses hit zero.
- A first-class timer trigger type is cleanup, not a necessity â€” the workaround already covers the core need.
- Add a trigger type with a `duration`/`ticks` field that auto-fires at expiry.
- Reuse the existing on_tick hook so the countdown runs without extra engine machinery.

## Files

- engine/trigger_system.py â€” add first-class timer trigger type with duration/ticks field and expiry auto-fire
- engine/effects.py â€” support effects tied to the timer trigger firing

