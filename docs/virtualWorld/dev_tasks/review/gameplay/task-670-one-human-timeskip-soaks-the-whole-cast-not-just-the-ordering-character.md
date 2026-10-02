---
type: task
status: review
area: gameplay
priority: medium
---

# task-670: One-human timeskip soaks the whole cast, not just the ordering character

**Filed:** 2026-10-02
**Related:** task-481, task-464, task-482

## Goal

Confirmed design 2026-10-02: 0 attended humans -> world advance with everyone in soak; 1 attended human -> the same blocking advance, with the ordering character on its declared intent and EVERY other character on background fidelity for the span; 4+ attended humans -> a soak order carried by the turn loop. The middle case is built wrong: timeskip.advance leaves nearby NPCs and agents at active fidelity, so a one-human wait runs LLM turns for the cast instead of backsim. Fix by sharing advance_world's everyone-soaked span helper.

## Acceptance

- [x] `engine/timeskip.everyone_soaking(gs)` is the single everyone-soaked span:
      snapshot every `simulation_mode`, force `background`, restore in `finally`.
- [x] `advance_world` (no human) uses it — unchanged behaviour, one mechanism.
- [x] `advance` (one human) uses it: the ordering character still acts on its
      declared intent in step 1, and nobody holds a focused turn for the span.
- [x] The restore also covers a `tick_turn` that raises.
- [x] A regression test measures the modes from *inside* `tick_turn` (the span,
      not just the restore), plus the restore and the exception path.
- [x] The route case is pinned: alone -> `mode: "character"` (blocks, declares no
      order) with the cast soaked mid-skip.
- [ ] Live solo confirmation in the browser (a one-human `POST /api/world/timeskip`
      with another character in the area) — **blocked**, see Progress.
- [ ] Full pytest lane green — **blocked**, see Progress.

## Progress — 2026-10-02

**Also fixes a display bug found on the way.** The soak-order envelope
(`{ok, mode: "soak", order}`) carries no elapsed figures, but
`static/js/ui/timeskip.js` printed `data.elapsed_minutes` unconditionally, so the
dialog showed `Elapsed: undefined min (undefined ticks)`. Measured live: the POST
returned `{mode: "soak", ok: true, order: {...}}` with exactly those three keys
missing. The summary now branches on `mode` and describes the order instead; the
render is a pure `_summarize()` so it is unit-testable, with 3 new cases in
`tools/unit/test_timeskip.js`.

**Engine change.** `advance_world` had the everyone-soaked block inline;
`advance` had none. Both now share `everyone_soaking`. This also removes a latent
double-act: `process_due` gives a focused character `minutes_in_turn - 1` minutes
(zero at a 1-minute tick), which is the task-436 root cause `advance_world` already
guarded against and `advance` did not.

**First attempt was wrong and the tests caught it.** Backgrounding *everyone*
(hero included) handed the ordering character to the deterministic runner, which
**moved them**: an `idle` ("wait here — do nothing") skip walked Arix out of the
area, and because the social-approach seam is "a co-located background character
reaches the active character" (`background_social.run_social_approach`), every
co-located interrupt lost its subject. Two existing tests failed
(`test_timeskip_pauses_on_a_social_approach`, and
`test_vital_danger_interrupts_and_returns_control` now firing `threat:attack`
before `vital:thirst`); both were confirmed mine by stubbing
`everyone_soaking` back to a no-op, where they pass again. Fix: `everyone_soaking`
takes `keep=` and `advance` passes the ordering character — the same rule a
declared soak order runs under, where `process_due` skips the ordered character so
the generic need policy never competes with the declared intent.

**Verified.** `tests/test_timeskip.py test_soak_orders.py test_soak_chain.py
test_fear.py test_social_approach.py` -> **95 passed**. Both new tier tests were
checked against a no-op stub of `everyone_soaking` and **fail** there, so they
discriminate. JS gates clean.

**Verified in the browser** (second instance on :4455 so the live :4444 session
was untouched; Jake flipped to `autonomy: true` there so the one-human branch was
reachable). Real click-through — Game ▾ → Wait / Timeskip… → 30 min → Skip:

- response `mode: "character"` with `elapsed_minutes: 13`, `ticks: 13`,
  `clock_after: "08:14:00"` — the blocking branch, not an order, and no
  `undefined` anywhere;
- **Arix stayed in `Chief's Pit`** while the cast moved (Eldenford Blacksmith /
  Elder / Farmer all relocated to `Road (world 18,3)` and `Road (world 15,7)`);
- the social interrupt fired and ended the skip early — `Interrupted: Vekka jokes
  with Arix.` — which is the regression the first attempt had killed;
- the dialog rendered `Elapsed: 13 min (13 ticks) → 08:14:00`, the interrupt line,
  the vitals deltas and the notable-lines tail.

The tier flip itself is engine-level evidence, not browser evidence:
`simulation_mode` is not part of the `/api/state` payload, so the browser can show
that the cast advanced and the hero did not wander, while the A/B above shows *how*
they advanced.

## Still open

- The 4-human soak-order path is unchanged by design and re-verified by
  `test_soak_orders.py`; its own summary display was the `undefined` fix above.
- `git stash` was not used (shared-worktree rule); the A/B was done by stubbing
  the new seam back to a no-op, which is behaviourally identical to its absence.
