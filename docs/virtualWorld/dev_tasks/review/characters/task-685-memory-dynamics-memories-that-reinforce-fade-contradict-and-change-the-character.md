---
type: task
status: review
area: characters
priority: high
children: [task-686, task-687, task-688, task-689, task-690, task-691]
---

# task-685: Memory dynamics: memories that reinforce, fade, contradict, and change the character

**Filed:** 2026-10-04
**Related:** task-178, task-346, task-403, task-350
**Design doc:** `docs/virtualWorld/AI & Narration/Memory Dynamics.md`
**Interface mockup:** `docs/design/memory-mockup.html`

## Goal

Make memory a dynamic system instead of a static list: dynamic availability
(activation), confidence, reinforcement on recall and re-encounter, non-uniform
decay, belief-category memories, and contradiction links — all **additive** to
`Player.memories[]`. The test of the finished system is the question it can
answer: *what has happened to this character, what did they conclude from it,
how certain are they, how do they feel about it, and how has it changed what
they expect to happen next?*

## Children

| Task | Slice |
|---|---|
| task-686 | Engine: dynamics fields + reinforcement (recall + re-encounter) |
| task-687 | Engine: non-uniform decay (activation with per-memory resistance) |
| task-688 | Engine: reflection 2.0 — structured insights, depth guard, consolidation |
| task-689 | Engine: contradiction detection (marking, never resolving) |
| task-690 | Retrieval 2.0: one multi-signal scorer + structured recall block |
| task-691 | UI: Memory Mind interface per the mockup |

## Acceptance

- [x] Every child task done; the compatibility table in the design doc §8 still holds (HTC, agents, triggers, soak, observation memory, MCP, editor all operate unchanged) — children 686–691 in review; the full suite A/B against a clean master worktree shows identical failure names (the one apparent difference is the gitignored local `jessica.json`, unrelated).
- [x] An old save (no dynamics fields) loads, plays, saves, and reloads with no errors and no field loss (`test_old_save_memory_round_trips_without_new_fields`).
- [x] A play session demonstrably produces: reinforced memories (↻ counts rise), faded memories, at least one belief from reflection, and the structured I REMEMBER block in the prompt — demonstrated live on 2026-10-04: seeded a scenario, saw re-encounter reinforcement (↻ ×1), contradiction links (⚡ 1 pair), belief/procedural/social memories from one structured reflect, the derive.py profile (Anna: rival, trust −28), and the Memory Mind dashboard rendering all of it.
- [x] Documentation status markers updated from *planned* to *implemented/wired/authored/tested* per feature (Memory System.md + Memory Dynamics.md).

## Open questions

- Should reflection also run engine-side for NPCs who never get a client LLM
  turn (background_simulation path), or is client-side reflect() the only
  reflection writer? Today reflect() is client-only; background characters
  never reflect. Deliberately **not** solved in this tree unless it blocks
  task-688's wiring test.
- Default-on decay changes existing scenarios by design. Confirm the default
  rate (0.01/tick) feels right after one soak; `memory.decay_per_tick: 0`
  is the freeze hatch.
