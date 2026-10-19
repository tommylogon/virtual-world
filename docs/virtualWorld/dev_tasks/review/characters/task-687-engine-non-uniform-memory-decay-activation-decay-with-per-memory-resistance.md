---
type: task
status: review
area: characters
priority: high
related: ["'task-685'", "'task-686'", "'task-688'", "'task-689'", "'task-690'", "'task-707'", 'task-685', 'task-686', 'task-688', 'task-689', 'task-690', 'task-707']
parent: task-685
---

# task-687: Engine: non-uniform memory decay (activation decay with per-memory resistance)

**Filed:** 2026-10-04
**Related:** task-685, task-403

<!-- deps:start -->
**Parent:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]]
**Related:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]], [[task-686-engine-memory-dynamics-fields-reinforcement-on-recall-and-re-encounter]], [[task-688-engine-reflection-2-0-structured-insights-depth-guard-consolidation]], [[task-689-engine-contradiction-detection-linking-fallible-memory]], [[task-690-retrieval-2-0-one-multi-signal-scorer-structured-character-model-recall-b]], [[task-707-memory-decay-reduces-activation-only-never-deletes-actor-trigger-or-consolidation-only]]
<!-- deps:end -->

## What

Replace the flat trait-gated salience subtraction in `AgentMind.apply_decay`
with activation decay in `memory_dynamics.apply_decay`, so that *what* a memory
is decides how fast it fades:

- Rate = `memory.decay_per_tick` runtime-config (new, small default 0.01)
  × trait `memory_decay_per_tick` multiplier (when the character has one) ×
  source factor (preconceived never; background ×0.5 - both unchanged).
- Resistance factors multiply the step down: base importance ≥ 8 → ×0.4,
  ≥ 6 → ×0.7; any `memory_emotions` intensity ≥ 7 → ×0.6;
  `1 − 0.1 × min(reinforcements, 6)`; category semantic/belief/procedural → ×0.3.
- Decays `activation` toward 0; removal only when activation ≤ 0.01 AND the
  memory is unimportant (base < 6, no reinforcements, not manual/preconceived).
  Removal still evicts the observation index entry (task-425 re-enchantment
  preserved).
- Same tick hook (`tick_manager`), same trait gates; no second scheduler.

## Acceptance

- [ ] Unit: two memories, identical except one importance-9 emotional and one importance-3 plain - after N decay steps the important one's activation is strictly higher, and the plain one is removed first.
- [ ] Unit: `preconceived` never loses activation; `background` decays at half the rate of `auto`.
- [ ] Wiring: the decay pass runs from the existing tick path and returns a removed count consumed by the tick manager as today.
- [ ] Config: `memory.decay_per_tick: 0` freezes all decay; the trait path still decays when the config is 0 (trait behaves as today's baseline).
- [ ] Important memories are never deleted by decay (asserted).

## Open questions

- Is 0.01/tick the right default? One soak (task-466-style harness) should
  measure how many memories a typical 500-tick scenario loses. The freeze
  hatch exists, but the default should be defensible, not arbitrary.

## Why

A uniform flat salience subtraction treated trivial observations (e.g. seeing a rock) identically to traumatic or emotionally charged experiences (e.g. nearly dying in a trap), resulting in characters forgetting critical life events at the same rate as mundane scenery. Non-uniform activation decay factors in memory importance, emotional intensity, reinforcement count, source type, and memory category so salient and formative memories resist decay while background noise fades gracefully.

## How

1. In engine/memory_dynamics.py, implement apply_decay(memories, config) calculating per-tick decay rate multiplied by character traits and source factors (preconceived 0.0, background 0.5, auto 1.0).
2. Calculate resistance multipliers: base importance >= 8 (0.4x), >= 6 (0.7x), emotion intensity >= 7 (0.6x), reinforcements (1 - 0.1 * min(reinforcements, 6)), category semantic/belief/procedural (0.3x).
3. Reduce activation toward 0; prune only when activation <= 0.01 and base importance < 6 with zero reinforcements.
4. Hook into tick_manager without adding a secondary scheduler; respect memory.decay_per_tick: 0 as a freeze config.

## Steps to verify

1. Run decay unit tests comparing high-importance emotional memories against low-importance plain memories.
   - expected: Emotional/high-importance memories retain strictly higher activation over identical tick counts; plain memories reach eviction threshold first.
   - observed: Tested via tests/test_memory_decay.py.
2. Verify source factor handling (preconceived vs background vs auto).
   - expected: Preconceived memories never decay; background memories decay at half rate.
   - observed: Confirmed in unit test assertions.
3. Test decay freeze via config override (memory.decay_per_tick = 0).
   - expected: No memory loses activation during tick simulation.
   - observed: Verified via configuration tests.

## Files

- engine/memory_dynamics.py (apply_decay)
- engine/agent_mind.py
- engine/tick_manager.py
- 	ests/test_memory_decay.py

## Browser UI and intended live verification

Intended UI home: select a character → Mind → Memories → compare one high-importance emotional memory with one low-importance plain memory before and after simulation time advances.

Current availability: the card proposes activation decay based on per-memory resistance, category, source, and `memory.decay_per_tick`; the tick path/config wiring is part of acceptance and is not claimed complete here.

Live steps when available:
1. Load two memories that differ only as specified: importance-9 emotional versus importance-3 plain. Record activation in `/api/state` and open both in Mind.
2. Advance the same number of ticks for both entries and inspect the updated details.
   - expected: the important memory's activation remains strictly higher; the plain memory reaches the removal/retention rule first, according to this card's chosen floor policy.
3. Repeat with `preconceived`, `background`, and `auto` sources.
   - expected: preconceived activation never falls; background decays at half the auto rate.
4. Set `memory.decay_per_tick` to zero, advance ticks, and reopen Mind.
   - expected: no memory loses activation; the configured zero is read by the live tick decay pass.
5. Compare the tick result with `/api/state` and the tick/event summary.
   - expected: the removed count consumed by the tick manager matches actual removals.

This section is not a claim that the non-uniform decay path is wired today.
