---
type: task
status: todo
area: gameplay
priority: high
horizon: now
effort: L
wiki: "[[AI & Narration/Cognitive Memory & Active Mind]]"
tags: [memory, cognitive-architecture, intermediator, soak, lived-log, prompt-pipeline]
related: [task-944, task-943, task-908, task-909, task-727, task-685]
---

# task-947: Memory intermediator and reconsolidation palimpsest pipeline

**Filed:** 2026-11-12
**Related:** task-944, task-943, task-908, task-909, task-727, task-685

<!-- deps:start -->
**Related:** [[task-944-subjective-cognitive-memory-and-active-mind]], [[task-943-two-stage-actor-to-interpreter-pipeline]], [[task-908-associative-memory-retrieval-3-0-multi-facet-perceptual-cues-and-zero-padding-prompt-lanes]], [[task-909-dedicated-memory-model-client-and-agentlens-live-retrieval-comparison-sandbox]], [[task-727-lived-log-to-memory-bridge-phrase-lived-entries-into-first-person-memories]], [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]]
<!-- deps:end -->

## What

Replace start-of-turn/end-of-turn Actor memory creation and raw memory or observation dumps with a dedicated Memory Intermediator stage: observations -> involuntary recall -> synthesized conscious memory (varnished palimpsest) -> inner monologue, thought, and plan -> decision, questions, assumptions, and reactions. Never expose raw past observations (including soak lived_log entries) or raw stored memory records directly to the acting/planning LLM.

## Why

Prompting the Actor at turn start or end with 'what do you want to remember going forward' forces future-oriented memory creation at the moment events occur instead of through natural recollection. Meanwhile, task-944 and Cognitive Memory & Active Mind.md currently inject raw === I REMEMBER === memory traces directly into the Actor prompt, and soak runs lose coherence when raw past lived_log observations are fed as context. Modeling recollection via an Intermediator reconstructs recalled traces alongside present observations into a varnished conscious memory summary paired with inner monologue persistence, unifying interactive turns and soak lived_log continuity.

## How

1. Pipeline reorder (aligning with task-943 and task-944): split turn cognition into (a) sensory observations + involuntary multi-hop recall (engine/memory_retrieval.py), (b) Intermediator synthesis on getMemoryLLMClient() (task-909), (c) Actor inner monologue, thought, plan, assumptions, and reactions consuming ONLY current observations plus the Intermediator's conscious memory summary, and (d) persistence saving the newly synthesized conscious memory and inner monologue back to memory with reinforcement/invalidation feedback to engine/memory_dynamics.py.
2. Strict Actor Isolation Contract: remove raw stored memory lists and raw historical lived_log/observation history from Actor/planning prompt builders (static/js/agent/prompt-builder/memory-context.ts, turn-prompts.ts, engine/soak.py). Retire vestigial endOfTurnMemory / Reactor memory-creation paths once Intermediator output is wired.
3. Reconsolidation palimpsest semantics with Two-Lane Factual Invariant: apply subjective varnishing/reinterpretation strictly to episodic, social, emotional, and narrative beliefs. Keep deterministic state (inventory, spatial_memory topology, door/lock states, and AlreadyKnown absence/examination guards) on an unvarnished factual lane so biased recollection cannot hallucinate keys or break PlanGrounding.
4. Auditability & anti-drift lineage: keep raw immutable source observation refs (and generation depth metadata) alongside derived conscious memory syntheses in backend storage/routes (routes/memories.py, engine/lived_log_memory.py) so multi-turn soak runs do not compound hallucination cascades and Inspector views can trace how a memory drifted.
5. Latency & cue-change gating: execute Intermediator synthesis with lightweight getMemoryLLMClient(), skip re-synthesis when no new significant observation/recall cue shifted on continuation ticks, and benchmark p95 turn time alongside task-943 Actor/Interpreter stages.

## Browser UI and intended live verification

Intended UI home: Not applicable

Current availability: Turn pipeline in static/js/agent-engine.ts and backend memory services in engine/ is active; Intermediator synthesis stage is planned.

Why no browser UI: This task restructures prompt orchestration, Actor context isolation, and memory reconsolidation backend flow; interactive Mind/Inspector display adjustments remain tracked cleanly via routes/memories.py payloads and companion UI tasks.

Alternative verification steps:
1. Run Actor prompt assembly tests verifying raw historical observations and raw memory DB rows are absent from Actor/planning prompts.
   - expected: Actor prompt includes current observations and Intermediator conscious synthesis only, with zero raw memory traces or raw lived_log history.
2. Run soak lived_log-to-memory continuity test confirming synthesized conscious memory and inner monologue feed the next turn without raw observation leakage.
   - expected: Each turn synthesizes a varnished subjective memory paired with inner monologue while deterministic spatial/inventory/AlreadyKnown state stays uncorrupted.
3. Inspect /memories debug payloads to verify both raw source lineage and varnished conscious synthesis metadata are recorded.
   - expected: Stored conscious memories retain links to immutable source observation refs and generation depth for auditability.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Run Actor prompt assembly tests with populated memory DB and soak lived_log entries.
   - expected: Actor prompt receives current observations and the Intermediator conscious synthesis block only, with zero raw memory rows or raw historical observations.
   - observed: Pending Intermediator implementation after alignment with task-944.
2. Execute a multi-turn scenario recalling a key/locked-door memory alongside new sensory observations.
   - expected: Intermediator synthesizes a varnished conscious episodic memory while keeping spatial topology, inventory, and AlreadyKnown checks on the unvarnished deterministic lane.
   - observed: Pending Intermediator implementation.
3. Benchmark turn latency across continuation ticks with getMemoryLLMClient() cue-change gating enabled.
   - expected: Unchanged ticks reuse the prior conscious synthesis without an extra LLM call.
   - observed: Pending profiling.

## Acceptance

- [ ] Actor and planning prompts receive zero raw stored memory records and zero raw historical lived_log/observation transcripts.
- [ ] Dedicated Intermediator stage consumes current observations, involuntary recall, and lived_log summaries to produce a synthesized conscious memory plus dynamics reinforcement/invalidation updates.
- [ ] Synthesized conscious memory and Actor inner monologue are both persisted back into memory storage after cognition.
- [ ] Two-lane factual invariant prevents subjective palimpsest varnishing from corrupting inventory, spatial routes, or AlreadyKnown grounding checks.
- [ ] Raw source observation lineage remains traceable alongside derived conscious memories in routes/memories.py payloads.
- [ ] Soak simulation uses the same Intermediator conscious-summary handoff across long runs without raw observation leakage.

## Files

- `static/js/agent-engine.ts`
- `static/js/agent/memory-manager.ts`
- `static/js/agent/action-interpreter.ts`
- `static/js/agent/prompt-builder/memory-context.ts`
- `static/js/agent/prompt-builder/turn-prompts.ts`
- `engine/memory_retrieval.py`
- `engine/memory_dynamics.py`
- `engine/lived_log.py`
- `engine/lived_log_memory.py`
- `engine/soak.py`
- `routes/memories.py`
- `docs/virtualWorld/AI & Narration/Cognitive Memory & Active Mind.md`
