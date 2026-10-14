---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
---

# task-825: Simultaneous mode v2: async cooldown timers with talkativeness

**Filed:** 2026-10-14
**Related:** task-824

## What

Replace the current simultaneous turn mode (everyone acts at once in a batch)
with independent per-character async cooldown timers. Each character acts on
their own timer, controlled by a per-character "talkativeness" slider that sets
their cooldown range. This is a core engine/turn-system improvement, not
specific to any single page.

## Why

The current simultaneous mode processes all characters at once, which feels
artificial. Real conversations and group behavior have pacing — some characters
are quick to act, others deliberate. Per-character async timers with
talkativeness produce emergent pacing that feels natural without requiring
strict turn order.

## How

- Per-character **talkativeness** slider (or personality-derived value):
  controls cooldown range from ~5 seconds (chatty) to ~2 minutes (quiet).
- Cooldown includes **randomness/jitter** so characters don't fire at
  predictable intervals.
- When a character's cooldown expires, they run the standard agent loop
  (memory recall → decide → act → write subjective memory).
- If two characters fire at the same moment, both proceed — order by arrival
  time, no conflict resolution needed (the Discord model).
- **Pause/resume** control: global pause button, auto-pause when tab loses
  focus.
- **Rate awareness**: surface character count × average pace so the user
  understands API cost at current settings.

## Integration

This replaces or augments the "simultaneous" option in the existing turn mode
selector. The turn mode selector should offer:

| Mode | Behavior |
|---|---|
| No turns | As today |
| Sequential | Round-robin, one at a time |
| Random | Random order per round |
| Simultaneous (async) | Independent per-character cooldown timers (this task) |

The existing turn-queue.js infrastructure handles sequential/random. This task
adds the async timer path alongside it.

## Steps to verify

1. Set turn mode to simultaneous (async).
   - expected: characters begin acting independently on their own timers.
   - observed: TODO

2. Adjust talkativeness slider for one character to minimum (5s).
   - expected: that character acts roughly every 5–10s with jitter.
   - observed: TODO

3. Adjust talkativeness slider for one character to maximum (2min).
   - expected: that character acts roughly every 1.5–2.5min with jitter.
   - observed: TODO

4. Pause the system.
   - expected: all timers freeze, no API calls.
   - observed: TODO

5. Tab loses focus.
   - expected: auto-pause, resumes on focus.
   - observed: TODO

## Acceptance

- [ ] Per-character talkativeness slider (5s–2min range with jitter).
- [ ] Characters fire independently on their own cooldown timers.
- [ ] Standard agent loop runs on each firing (recall → decide → act → memory).
- [ ] Concurrent firings resolve by arrival order, no conflict.
- [ ] Global pause/resume.
- [ ] Auto-pause on tab unfocus.
- [ ] Rate/cost indicator visible to user.
- [ ] Integrates with existing turn mode selector as the "simultaneous" option.

## Files

- TODO: turn-queue.js or new async-timer module
- TODO: per-character talkativeness state/config
- TODO: UI for talkativeness slider and pause control
