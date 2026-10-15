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

## Browser UI and intended live verification

Intended UI home: turn-mode selector → **Simultaneous** → per-character talkativeness controls and global pause/resume; observe each firing in the event stream and the rate/cost indicator.

Current availability: the card proposes replacing batch-at-once simultaneous turns with independent asynchronous cooldowns. Per-character cooldowns, talkativeness, auto-pause, and rate/cost display are planned; the current simultaneous mode is not described as having these controls.

Live steps when available:
1. Choose simultaneous mode and set two characters to visibly different talkativeness values, one near 5 seconds and one near 2 minutes. Start the simulation and inspect timestamps in the event stream.
   - expected: each character fires on its own jittered cooldown range rather than both firing in one shared batch; the higher talkativeness character fires more often.
2. Pause globally, wait longer than both cooldowns, then resume.
   - expected: no character acts while paused; resumed timers continue without duplicate or simultaneous catch-up actions.
3. Move focus to another browser tab and return.
   - expected: the simulation auto-pauses on unfocus and remains paused until the user resumes it.
4. Observe the rate/cost indicator while both characters run.
   - expected: it reflects the actual firing rate and model usage; concurrent actions resolve in arrival order without lost or duplicated events.

This section is not a claim that planned UI exists or works today.
