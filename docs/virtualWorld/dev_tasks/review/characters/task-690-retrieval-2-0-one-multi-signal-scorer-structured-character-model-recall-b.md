---
type: task
status: review
area: characters
priority: high
parent: task-685
---

# task-690: Retrieval 2.0: one multi-signal scorer + structured character-model recall block

**Filed:** 2026-10-04
**Related:** task-685, task-91, task-350

<!-- deps:start -->
**Parent:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]]
<!-- deps:end -->

## What

Stop "give the agent 10 important memories"; start "give the agent the memories
this situation makes relevant, plus the conclusions it has already drawn":

- **Backend** `/memories/retrieve` becomes the one scorer:
  - filters suppressed (active), superseded, textless — today the endpoint
    forgets both filters that `Player.get_relevant_memories` applies; they must
    agree;
  - signals: keyword overlap, entity-graph match (query names/ids vs
    `entity_ids` — relationship history beats vector noise), exponential
    recency (half-life ≈ 300 ticks; the current linear `1 − tick/500` goes
    negative past tick 500), `effective_importance` (task-686), emotion match
    (an emotion word in the query boosts memories encoded with it);
  - **seat time guarantee**: when belief/semantic memories match the query's
    entities, top slots reserve room for them even when episodic matches
    outscore them;
  - `structured: true` response adds `groups: {events, beliefs, social,
    expectations}` over the same memories — a view, not a second store.
- **Client** `buildMemoryContext`: builds the query from the situation (area +
  last thought + heard lines + current interlocutor / active `rel:` context);
  requests `structured: true`; renders the I REMEMBER block as
  EVENTS / WHAT I BELIEVE / HOW I SEE PEOPLE / WHAT I EXPECT. Vector merge and
  text dedup keep working (they merge by id/text as today); recall feedback
  line (`recalled N · …`) stays.
- Agent Lens preview mode keeps its no-side-effects guarantee (no
  reinforcement, no embedding calls).

## Acceptance

- [ ] Unit: scorer ranks a same-entity episodic memory above a higher-importance unrelated one for an entity-targeted query; suppressed and superseded entries never return.
- [ ] Unit: recency term is ≥ 0 for a tick-5000 memory (old linear score was negative).
- [ ] Unit: structured groups contain only memories that also appear in the flat list; a belief matching the entity appears in the top-3 slots when present.
- [ ] Wiring: prompt block built from a live character contains all four section headers when the character has matching memories of each kind; sections collapse gracefully (absent kinds omit their header).
- [ ] The recall feedback line still reports what was retrieved and why.

## Open questions

- Half-life 300 ticks is a guess; tie it to `memory.decay_per_tick` so decay
  and recency share one notion of "how long ago is old"? Leaning yes — one
  constant, two consumers.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: run a character turn or deliberate `recall` request → inspect the raw prompt/agent context and the character's Mind memory list for the retrieved memories and structured groups.

Current availability: the card proposes one multi-signal `/memories/retrieve` scorer, filters for suppressed/superseded entries, and structured character-model groups. The unified retrieval/prompt view is not claimed as complete.

Live steps when available:
1. Give a character one same-entity episodic memory and one higher-importance unrelated memory; request recall of that entity.
   - expected: the same-entity memory ranks first, while suppressed, superseded, and textless entries never appear.
2. Load a recent memory at tick 5000 and inspect the ordered results.
   - expected: its recency contribution is non-negative; old tick arithmetic does not push it below zero.
3. Open the agent prompt context for a live character turn.
   - expected: the flat list and all four structured groups refer to the same memory IDs; a matching belief appears in the top three slots when present.
4. Inspect an entity-targeted query and its entity IDs in the retrieval response.
   - expected: relationship/history evidence for that entity can outrank unrelated importance, and no hidden character name is introduced beyond what the character knows.

This section is not a claim that unified retrieval is wired through every prompt path today.
