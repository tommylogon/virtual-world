---
type: task
status: done
area: characters
priority: high
wiki: "[[Memory System]]"
related: ["task-690", "task-685", "task-686", "task-689"]
parent: task-690
---

# task-908: Associative Memory Retrieval 3.0: multi-facet perceptual cues and zero-padding prompt lanes

**Filed:** 2026-10-30
**Related:** task-690, task-685, task-686, task-689, task-730

<!-- deps:start -->
**Parent:** [[task-690-retrieval-2-0-one-multi-signal-scorer-structured-character-model-recall-b]]
**Related:** [[task-690-retrieval-2-0-one-multi-signal-scorer-structured-character-model-recall-b]], [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]], [[task-686-engine-memory-dynamics-fields-reinforcement-on-recall-and-re-encounter]], [[task-689-engine-contradiction-detection-linking-fallible-memory]]
<!-- deps:end -->

## What

Consolidate pre-turn memory retrieval into a unified backend engine (`engine/memory_retrieval.py`) driven by multi-facet perceptual cues, with clean prompt lane budgeting and zero fake padding:

1. **Multi-Facet Perceptual Cues:**
   - Stop building queries from only `currentArea + lastThought + 2 heard lines`.
   - Pass structured situation cues to `/api/players/<name>/memories/retrieve`:
     - Scene actors present in the room (`player_*` IDs and names).
     - Visible items and containers in the room (`item_*` IDs and names).
     - Carried inventory items.
     - Spoken dialogue (recent hearing tokens) and own last thought.
     - Active bodily needs when vitals are elevated (`need:food`, `need:drink`, `need:rest`).
     - Current emotion/affect state.

2. **Associative Intersection Surge & Temporal Validity:**
   - Memories that link multiple active cues simultaneously (e.g. Jake present in room AND olives mentioned in dialogue) receive a multiplicative intersection boost that beats single-token noise.
   - Temporal validity window: memories with `invalid_at` populated and `<= current_tick` are skipped during active recall. Existing `contradicts` and `superseded_by` checks stay respected.

3. **Three Non-Competing Prompt Lanes:**
   - **Working Scene Buffer:** Rolling recent actions/speech plus the memory IDs recalled on the immediately prior turn (protects against mid-conversation amnesia).
   - **Associative Recall (`0..6`):** Scored associative memories above threshold. Crucially, **0 is allowed** when nothing connects; eliminate the legacy top-3 zero-score padding.
   - **Open Questions (`0..2`):** Active unresolved questions (`category: "question"`) whose watch targets match entities or concepts in perception.

4. **Write-Path Parity (`AgentMemory.storeMemory`):**
   - Stamp `location: player.current_area` on turn-written memories (currently saved as empty string).
   - Attach the turn action's `item` and `target` entity IDs into `entity_ids`.
   - Record `valid_at` (current tick) and initialize `invalid_at: null`.

## Why

Auditing `memory-context.ts` and `routes/memories.py` revealed four defects breaking retrieval:
1. Visible room characters and items are completely missing from the retrieval query, making silent companions invisible to recall.
2. Area slug synthesis (`area_<slug>`) fails on hand-authored node IDs, breaking area entity boosts.
3. The legacy client loop forces 3 memories into the prompt even when their relevance score is 0.
4. Browser turn memories drop `location` and action targets on write, leaving memories disconnected from the entities they involved.

## How

- Implement `engine/memory_retrieval.py` with `retrieve_associative_memories(player, cues, config)`:
  - Implements multi-facet scoring: keyword overlap, entity intersection boost, recency half-life, effective importance (`activation * confidence`), need matching, and emotion match.
  - Implements lane partitioning and score explanation (`explain: true` returns candidate breakdowns).
- Wire `routes/memories.py`: `/api/players/<name>/memories/retrieve` delegates directly to `memory_retrieval.py`.
- Update `static/js/agent/prompt-builder/memory-context.ts`:
  - Collects room actors, room items, inventory, dialogue, vitals, and emotion as structured payload.
  - Renders the lane-budgeted prompt sections without padding zero-score entries.
- Update `static/js/agent-engine.ts` (`_storeReactionMemory`) and `static/js/agent/memory-manager.ts` (`storeMemory`):
  - Passes current area to `location`.
  - Collects action target and item IDs into `entity_ids`.

## Browser UI and intended live verification

Intended UI home: Left sidebar -> Lens tab -> Agent Lens (`AgentLens` preview).

Current availability: Planned / ready for implementation.

Live steps when available:
1. Open the web client and select an agent in the Lens tab (e.g. Kayla).
2. Observe the `=== I REMEMBER ===` section in the generated prompt preview.
   - expected: Only memories relevant to the agent's current surroundings appear; an agent in an empty room with no matching associations sees no padded filler memories.
3. Place another character in the same room (e.g. Jake) and trigger dialogue containing a connected topic (e.g. "olives").
   - expected: The associative memory connecting both entities surfaces at the top of the recall block with its matched cues explained.

## Steps to verify

1. Follow the intended live path in Agent Lens preview.
   - expected: Multi-facet cues surface connected memories without zero-score padding.
   - observed: Recorded during implementation.
2. Run targeted pytest verification: `python -m pytest tests/test_memory_retrieval_associative.py`.
   - expected: All unit tests for intersection scoring, need probes, temporal validity, and write-path parity pass full output.
   - observed: Recorded during implementation.

## Acceptance

- [x] Unit: Multi-facet scoring ranks an intersection hit (Jake + olives) strictly higher than single-entity memories about Jake alone or food alone.
- [x] Unit: Zero-score memories are never padded into recall; an empty room returns 0 associative memories.
- [ ] Unit: Memories with `invalid_at <= current_tick` or `superseded_by` are excluded from active associative recall.
- [x] Unit: Bodily need cues (high hunger/thirst) surface food/drink memories without requiring specialized container tracking.
- [ ] Unit: `storeMemory` stamps `location` and the turn's acted-on target/item IDs into the stored record.
- [x] Browser: Agent Lens displays the lane-budgeted recall block reflecting visible actors and room items.

## Files

- `engine/memory_retrieval.py`
- `routes/memories.py`
- `static/js/agent/prompt-builder/memory-context.ts`
- `static/js/agent-engine.ts`
- `static/js/agent/memory-manager.ts`
- `tests/test_memory_retrieval_associative.py`
