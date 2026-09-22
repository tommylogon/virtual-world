---
type: task
status: todo
area: world
priority: high
---

# task-466: Interrupt & relevance evaluator (shared by timeskip, fidelity, soak)

**Filed:** 2026-09-22
**Related:** task-464, task-411, task-418, task-399, task-403

## Goal

One deterministic relevance/interrupt evaluator shared by timeskip actions (task-464), attention/fidelity tiers (task-411/418), soak deferral (task-399) and memory salience (task-403). Given a character and a tick's world deltas plus trace events, decide what they notice and must react to: threat (attack/steal/grapple/hostile approach), vital or condition threshold crossings, involuntary-action firing, discoveries matching interest tags or known goals, arrivals and sounds carried by awareness channels. Emits structured interrupt reasons (why-tags) and never calls an LLM. Stopping at a tick boundary means the post-interrupt state is an ordinary world state.

## Acceptance

- TODO
