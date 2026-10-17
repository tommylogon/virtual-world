---
type: feature
feature_id: 26
status: wired
section: in-game
tags: [status/wired, surface/in-game, system/characters]
---

# Activities & states

**What you can do:** Multi-tick activities; busy, unconscious, asleep

## How it works

- [[Activities & States]]

## Where it lives

_Not recorded yet — add the code paths when you next touch this feature._

## Bare-command defaults

A bare activity command (no number) gets a bounded default **except where the
activity has a natural wake condition**. Recorded so the next reader does not
"fix" the ones that are open-ended on purpose.

| Verb | Bare default | Why |
|------|-------------|-----|
| `rest` | 10 minutes | task-339: an unbounded rest let miki rest into the void |
| `wait` | 1 tick | a wait has no wake condition; open-ended meant forever |
| `sleep` | open-ended | wakes when Energy is full — the condition *is* the duration |
| `meditate` | open-ended | same as sleep; no natural end |

The route dispatch is `routes/action_handlers.py`; the engine methods are
`VirtualWorld.rest` / `wait` / `sleep` / `meditate` in `virtual_world_engine.py`.
`_activity_duration_ticks` converts minutes to ticks; a `None` duration means
"no timer, wake on the activity's own condition".

## Connected

- Feature Map: [[Feature Map|row 26]] (In a game)
- Sibling features: [[look-around]], [[examine]], [[move]], [[open-close]], [[take-drop-give]], [[use-use-on]]
- All features: [[Features Overview]]

> [!note] Status — `wired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-05. This page is an entry point; the
> deep documentation is linked under **How it works**.
