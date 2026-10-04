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

## Goal

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
