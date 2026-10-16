---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
parent: task-824
blocked_by: [task-824]
---

# task-854: Integrate The Commons with world actions and items

**Filed:** 2026-10-16
**Related:** task-824, task-825, task-299

**Parent:** task-824

<!-- deps:start -->
**Blocked by:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]]
**Parent:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]]
<!-- deps:end -->

## What

Connect The Commons to the standard world-turn agent path and authored
item/world interactions. This is follow-up work split from task-824; do not
reopen or expand task-824 to include this integration.

## Why

The Commons currently runs communication decisions through its own
`CommonsAgent` loop. Integrating it with world turns and item-based
communication may make communication part of the shared simulation, but the
right action seam and authored behavior need to be traced before implementation.
The integration must preserve The Commons' channel privacy and explicit-read
rules, and must not create another Player identity, conversation store, or
memory system.

## How

- Trace the standard `AgentEngine` turn from Player state through prompt
  construction, memory recall, decision, parsing, action execution, and memory
  storage; compare it with the current `CommonsAgent` path.
- Inspect existing item, action, trigger, and communication-device systems
  before choosing how authored items and world actions should reach Commons.
  Reuse the existing simulation model; do not invent a second communication or
  delivery store.
- Decide and document which communication behaviors belong in world turns and
  which belong to item/world interactions before changing runtime behavior.
  Keep any physical delivery, distance, or device requirements aligned with
  task-299 rather than implying them in the Commons UI alone.
- Implement the smallest shared, concurrency-safe integration. Preserve
  channel membership authorization, per-character explicit read cursors, and
  the existing Player memory path. Do not route multiple in-flight character
  decisions through unsafe shared mutable AgentEngine state.
- Add a focused mechanism test and a minimal authored scenario or item example
  that demonstrates the wired behavior, then verify it through the real
  browser/game surface.

## Browser UI and intended live verification

Intended UI home: The Commons page plus the applicable standard turn controls
and authored item interaction surfaces. The exact item/world surface depends
on the existing systems found during the initial trace.

Current availability: Planned; task-824 implements the standalone Commons
communication surface. Standard world-turn and item/world integration have not
been demonstrated.

Live steps when available:
1. Start a scenario with an authored communication opportunity and let an
   eligible character take a standard turn.
   - expected: the standard agent path can choose and execute an authorized
     Commons action, or use the authored item/world mechanism as specified by
     the verified design; the result appears in the appropriate channel and
     preserves explicit reads and channel privacy.
2. Inspect the acting character's Mind → Memories and the channel transcript.
   - expected: durable reflection uses the existing Player memory store; the
     channel transcript remains in The Commons, with no parallel mind or
     communication store.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Steps to verify

1. Trace the standard agent action path and the current Commons action path.
   - expected: identify a concrete shared integration seam and any concurrency
     constraints before changing behavior.
   - observed: TODO
2. Implement one authored end-to-end communication behavior through the
   selected world-turn/item interaction.
   - expected: an eligible character can perform the behavior in a scenario;
     channel authorization and explicit-read semantics remain enforced.
   - observed: TODO
3. Verify the behavior in the browser and with targeted regression tests.
   - expected: visible output, Player memory, and channel transcript match the
     design; no duplicate Player or communication state is created.
   - observed: TODO

## Acceptance

- [ ] The standard agent/world-turn integration is wired through a shared,
  concurrency-safe decision/action seam rather than a parallel character mind.
- [ ] Authored item/world interactions reach The Commons through existing
  action, trigger, and communication systems where appropriate; no duplicate
  delivery or conversation store is introduced.
- [ ] Channel membership, per-character explicit reads, and Player memory
  behavior remain intact.
- [ ] An authored scenario or item exercises the implemented integration.
- [ ] Targeted mechanism tests and live browser verification demonstrate the
  integrated path.

## Files

- `static/js/commons/` and the standard agent/turn integration surface, as
  identified by the initial trace
- Existing item/action/trigger and communication-device systems, as required
- Focused regression tests and authored scenario/item content
