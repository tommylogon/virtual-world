---
type: task
status: review
area: characters
priority: high
parent: task-685
---

# task-687: Engine: non-uniform memory decay (activation decay with per-memory resistance)

**Filed:** 2026-10-04
**Related:** task-685, task-403

## Goal

Replace the flat trait-gated salience subtraction in `AgentMind.apply_decay`
with activation decay in `memory_dynamics.apply_decay`, so that *what* a memory
is decides how fast it fades:

- Rate = `memory.decay_per_tick` runtime-config (new, small default 0.01)
  × trait `memory_decay_per_tick` multiplier (when the character has one) ×
  source factor (preconceived never; background ×0.5 — both unchanged).
- Resistance factors multiply the step down: base importance ≥ 8 → ×0.4,
  ≥ 6 → ×0.7; any `memory_emotions` intensity ≥ 7 → ×0.6;
  `1 − 0.1 × min(reinforcements, 6)`; category semantic/belief/procedural → ×0.3.
- Decays `activation` toward 0; removal only when activation ≤ 0.01 AND the
  memory is unimportant (base < 6, no reinforcements, not manual/preconceived).
  Removal still evicts the observation index entry (task-425 re-enchantment
  preserved).
- Same tick hook (`tick_manager`), same trait gates; no second scheduler.

## Acceptance

- [ ] Unit: two memories, identical except one importance-9 emotional and one importance-3 plain — after N decay steps the important one's activation is strictly higher, and the plain one is removed first.
- [ ] Unit: `preconceived` never loses activation; `background` decays at half the rate of `auto`.
- [ ] Wiring: the decay pass runs from the existing tick path and returns a removed count consumed by the tick manager as today.
- [ ] Config: `memory.decay_per_tick: 0` freezes all decay; the trait path still decays when the config is 0 (trait behaves as today's baseline).
- [ ] Important memories are never deleted by decay (asserted).

## Open questions

- Is 0.01/tick the right default? One soak (task-466-style harness) should
  measure how many memories a typical 500-tick scenario loses. The freeze
  hatch exists, but the default should be defensible, not arbitrary.
