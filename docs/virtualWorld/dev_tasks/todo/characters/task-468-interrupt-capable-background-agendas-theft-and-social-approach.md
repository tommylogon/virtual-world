---
type: task
status: todo
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
- [ ] Theft agenda: a trait/need-driven background character attempts `steal_item`
  on a co-located target (theft already emits a "notices" line the evaluator reads).
- [ ] Approach variety beyond `chat` (compliment/tease/confide by relationship band);
  currently forced to `chat` so the first touch is neutral.
- [ ] Agenda selection from traits/relationships (a bully, a thief, a flirt), not
  only the social pass's weighted draw.
