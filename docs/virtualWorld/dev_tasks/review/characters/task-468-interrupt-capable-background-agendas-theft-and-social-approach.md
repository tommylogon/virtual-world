---
type: task
status: review
area: characters
priority: medium
---

# task-468: Interrupt-capable background agendas: theft and social approach

**Filed:** 2026-09-22
**Related:** task-464, task-466, task-409, task-399, task-214

## Goal

Give background/soak policies the actor-driven agendas timeskip interrupts depend on:
theft (reuse `steal_item`) and deliberate social approach toward the player. Agenda
selection is deterministic, driven by traits, relationships, needs and schedule;
actions target co-located characters and write trace facts. Without this, waits and
fast-travels can never be meaningfully interrupted by other characters; the interrupt
evaluator (task-466) has nothing actor-driven to react to.

> **"Stalking" was a typo for "talking"** (the original ask was "steal from them,
> talk to them, or find something"). The social-approach half is done — see below.

## Acceptance

- [x] Deliberate social approach: `background_social.run_social_approach()` lets a
  co-located background character initiate a `chat` toward the active player, writes
  a `social_approach` turn event, and gives the player the memory; the timeskip
  interrupts with kind `social`. [[done in task-469 slice, tests/test_social_approach.py]]
- [x] Theft agenda: a trait/need-driven background character attempts `steal_item`
  on a co-located target (theft already emits a "notices" line the evaluator reads).
  [[`background_social.run_theft_pass`, tests/test_background_agendas.py]]
- [x] Approach variety beyond `chat` (compliment/tease/confide by relationship band);
  currently forced to `chat` so the first touch is neutral.
  [[`choose_approach_action`, band-gated; test_cold_band_never_confides_or_flirts,
  test_warm_band_can_confide]]
- [x] Agenda selection from traits/relationships (a bully, a thief, a flirt), not
  only the social pass's weighted draw. [[hostile→bully weights; `THEFT_TRAITS` +
  starvation motive drive theft; `attention_seeker`/`social_gain` drive flirt]]

## Progress — 2026-09-24

Implemented and tested; moving to review.

- **`engine/background_social.py`**
  - `APPROACH_ACTIONS` + `choose_approach_action()` — the approach toward the
    player now draws from the same weight table as the paired pass, restricted to
    non-hostile actions, so the band decides the kind (confide at friend, flirt at
    close friend) instead of always `chat`. Deterministic via the existing seeded
    RNG; falls back to `chat` when every option is gated out.
  - `run_theft_pass()` + helpers — a would-be thief (a `thief`/`kleptomaniac`/
    `pickpocket` trait or tag, or a starving character after food) makes a capped,
    cooled-down attempt through the **real** `steal_item` path (Sleight of Hand vs
    Perception), swapping the thief into the active slot and restoring it after.
    Writes a `why="agenda:theft"` trace; the failed attempt emits the same
    "notices" log line the interrupt evaluator reads.
- **`engine/background_simulation.py`** — `run_theft_pass` runs after the social
  pass each tick.
- **`tests/test_background_agendas.py`** (10) — approach is never hostile/no-op and
  is deterministic, band gating (cold never confides, warm can), hostile→bully
  weighting, tagged theft, starvation theft reaching only for food, cooldown +
  daily cap, a well-fed innocent does nothing, and the active player is restored.

Remaining: nothing mechanical; a scenario can author `thief` traits/tags and the
agenda does the rest.
