---
type: task
status: todo
area: gameplay
priority: medium
horizon: next
effort: M
wiki: "[[timeskip|Timeskip]]"
related: [task-671]
---

# task-859: A soak order promoted before it runs reports success and never says why it stopped

**Filed:** 2026-10-17
**Related:** task-671

<!-- deps:start -->
**Related:** [[task-671-a-timeskip-intent-that-cannot-be-carried-out-is-an-outcome-not-a-silence]]
<!-- deps:end -->

## What

`handle_timeskip` answers as soon as a soak order is declared (`routes/timeskip_ops.py:120-124`, `{ ok: true, mode: 'soak', order: {...} }`). The order is then carried by the turn loop, and `soak._step_one` checks `_promote_reason` at step 1 (`engine/soak.py:121`) before it runs the policy at step 2 (`engine/soak.py:130`). Any condition already true at the top of the turn promotes the character immediately, so a request can return success and move nothing. `_promote_reason` returns on a critical drive (`DRIVE_DANGER`, `engine/interrupts.py:25`), a low resource (`RESOURCE_DANGER`), a hostile condition, or a fear source. Measured 2026-10-17: a 120-minute explore on a character with Bladder 100 (band 90) ended on the order's first turn, `soak_end: Cullen Rutherford interrupted their soak: Your bladder is critical.`

## Why

The player is told the order was accepted and that control comes back early if something demands attention, but nothing tells them it actually did, or why. The only trace is a `soak_end` line in the event stream, so the skip reads as a silent no-op. The promotion itself is intended and tested (`tests/test_soak_orders.py::test_a_critical_vital_promotes_the_character`) - the gap is that the outcome and its reason are not surfaced back to the player who asked for the skip. Whether a full bladder should abort a skip at all, or be relieved by it, is an open question for the owner.

## How

Surface the promotion back to the requester: when an order declared by a timeskip request ends on its first turn (or any turn) before the span, report the promote reason instead of leaving the dialog at `control comes back early if...`. Reuse the existing `soak_end` detail as the reason text; do not add a second store for why an order ended. Do not change `DRIVE_DANGER` bands or the promotion order until the owner answers whether a critical need should abort a skip.

## Browser UI and intended live verification

Intended UI home: the timeskip result summary and the event stream. Current availability: the `soak_end` line exists in the stream; the dialog reports only that the order was declared. Live path: in a shared world, give the active character a critical vital (or a fear source in their area), request a timeskip, and confirm the dialog reports that the order ended and why.

## Steps to verify

1. In a shared world, set the active character's Bladder to 100 (or place a fear source in their area) and request a 120-minute explore.
   - expected: the dialog reports the order ended and the reason (`your bladder is critical`), not a bare success.
   - observed: TODO
2. Confirm the promotion mechanism is unchanged: `python -m pytest tests/test_soak_orders.py::test_a_critical_vital_promotes_the_character`.
   - expected: pass
   - observed: TODO

## Acceptance

- [ ] A soak order that is promoted before the span is spent is reported as an ended order with its reason, not an unqualified success.
- [ ] The reason comes from the existing promotion / `soak_end` path; no duplicate store.
- [ ] The existing critical-vital promotion test still passes.

## Files

- `routes/timeskip_ops.py` (`handle_timeskip` soak branch)
- `static/js/ui/timeskip.js` / the soak-order status surface
- `engine/soak.py` (`_step_one`, `_promote_reason` - reference)
