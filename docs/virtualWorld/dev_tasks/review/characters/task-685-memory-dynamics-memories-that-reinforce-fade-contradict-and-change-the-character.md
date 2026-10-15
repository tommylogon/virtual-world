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

<!-- deps:start -->
**Children:** [[task-686-engine-memory-dynamics-fields-reinforcement-on-recall-and-re-encounter]], [[task-687-engine-non-uniform-memory-decay-activation-decay-with-per-memory-resistance]], [[task-688-engine-reflection-2-0-structured-insights-depth-guard-consolidation]], [[task-689-engine-contradiction-detection-linking-fallible-memory]], [[task-690-retrieval-2-0-one-multi-signal-scorer-structured-character-model-recall-b]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]]
<!-- deps:end -->

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. In a live scenario, open the character's Memory Mind dashboard, re-encounter
   a known person, and inspect the recalled memory and derived person profile.
   - expected: the existing memory's reinforcement count rises and the profile
     reflects the recorded relationship evidence.
   - observed (2026-10-04): the card records reinforcement `↻ ×1`, one linked
     contradiction pair, structured reflection memories, and Anna's derived
     profile (`rival`, trust −28) in the dashboard.
2. Open a character with a contradictory pair and inspect both memory details.
   - expected: the two records remain in `Player.memories[]` and show a linked
     contradiction without one overwriting the other.
   - observed: the same live session recorded `⚡ 1 pair`; no fresh browser run
     was collected for this backfill.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio → 🧠 Mind → Memories / Memory Mind.

Current availability: The Memory Mind dashboard and the dynamics described in
this card were live-demonstrated on 2026-10-04. This records the card's existing
evidence; it is not a fresh browser check in this backfill.

Live steps when available:
1. Load a scenario with a character who has one reinforced memory and a linked
   contradiction; select that character, open Bio, scroll to the Memories
   section, and click 🧠 Mind.
   - expected: the dashboard shows the character's memory timeline, the
     reinforcement count on the recalled memory, and the contradiction link
     between the two records.
2. Run the scenario action that re-encounters the remembered person or event,
   reopen the same memory details, then open the character's derived profile.
   - expected: the same memory record's reinforcement count has increased and
     the profile reflects the relationship evidence; no second memory store is
     needed to explain either view.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
