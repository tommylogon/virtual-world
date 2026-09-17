---
type: task
status: todo
area: characters
priority: high
---

# task-403: Unified agent memory and knowledge system

**Filed:** 2026-09-17  
**Depends on:** task-324 (domain tags feed population queries), task-399
(background simulation needs memory consolidation)

## Goal

Collect the scattered knowledge systems already present in the codebase into
one coherent "mind" per agent, and add the missing pieces: pre-conceived
knowledge at scenario start, need-driven memory retrieval, and memory traits.

Current state: knowledge is spread across `Player.memories`,
`SpatialMemory`, `VectorStore`, `known_way_aspects`, `investigation_statuses`,
`traits`, `emotion` recall, and trigger `add_memory`. None of these share a
query interface. An agent cannot answer "where is food?" because that question
touches spatial memory, item tags, visited areas, and stored memories — and
there is no layer that joins them.

This task does not replace any existing system. It defines the unified model
and the seams between them.

## Unified memory model

Add `engine/agent_memory.py` with one class, `AgentMind`. It owns and
delegates to the existing subsystems:

```python
class AgentMind:
    def __init__(self, player, graph, vector_store=None):
        self.player = player
        self.spatial = SpatialMemory(graph)
        self.vectors = vector_store or VectorStore(...)
        self.traits = player.traits or {}

    def recall(self, query: str, need: str = None, context: dict = None) -> list[Memory]:
        """Return ranked memories relevant to query + optional need."""

    def remember(self, event: dict, tags: list[str] = None):
        """Store a structured event as a normal memory + embed it."""

    def know_area(self, area_name: str):
        """Mark an area as visited/known."""

    def knows_way(self, way_id: str, aspect: str = None):
        """Record a known way or way aspect."""

    def set_investigation(self, item_id: str, status: str):
        """Track investigation state on an item."""

    def consolidation_summary(self, since_tick: int) -> str:
        """Produce the bounded background-summary string task-399 requires."""
```

`AgentMind` is a facade. It does not reimplement storage. It calls through to
`player.memories`, `spatial.build_known_routes`, `vector_store.top_k`,
`player.known_way_aspects`, and `player.investigation_statuses`.

## Pre-conceived knowledge (scenario bootstrap)

Add `preconceived_knowledge` to scenario player entries and character templates:

```json
{
  "name": "goblin_scout",
  "memories": [
    {
      "text": "The camp food cache is in the pantry behind the kitchen.",
      "tags": ["food", "camp", "pantry"],
      "importance": 6,
      "salience": 7,
      "location": "kitchen",
      "tick": 0,
      "source": "preconceived"
    }
  ],
  "known_areas": ["camp_entrance", "kitchen", "pantry", "dining_area"],
  "known_items": ["item_dried_meat_01", "item_water_skin_01"],
  "known_ways": {
    "way_kitchen_to_pantry": ["hidden", "behind_shelf"]
  },
  "investigation_statuses": {
    "item_dried_meat_01": "seen"
  },
  "starting_route": {
    "from": "camp_entrance",
    "to": "kitchen",
    "via": ["way_camp_entrance_to_hallway", "way_hallway_to_kitchen"]
  }
}
```

At scenario load, `AgentMind.load_preconceived(player_data)` injects these
into the live player fields before the first tick. They are indistinguishable
from earned knowledge except for `source: "preconceived"` on memories.

**Design rule:** preconceived knowledge is not omniscient. A goblin camp scout
knows the pantry route because they were told; they do not know the locked
cellar unless it is listed. Their `known_areas` depth is authored, not
auto-derived from the whole graph.

## Need-driven memory retrieval

When a vital crosses a threshold, call `AgentMind.recall()` with the need as
query:

```python
needs = player.vitals.get_needs()
for need, urgency in needs.items():
    if urgency > THRESHOLD:
        memories = mind.recall(query=need, need=need, context={"area": player.current_area})
        if memories:
            player.add_memory({
                "text": f"While hungry, you recall: {memories[0].text}",
                "tags": [need, "recall"],
                "importance": memories[0].importance,
                "salience": memories[0].salience,
                "source": "need_recall"
            })
```

`recall()` uses three signals in order:
1. **Tag match** against `player.memories` and `implies` chains from tag files.
2. **Spatial match** via `SpatialMemory.build_known_routes` for the current
   area, filtered by visited-area set.
3. **Semantic match** via `VectorStore.top_k` for the query string.

The result is ranked by `importance * salience * urgency`. Needs that match
no memory produce a generic "you don't know where X is" prompt hint, not a
fabricated location.

## Memory traits

Add to `engine/traits.py`:

```json
{
  "name": "Perfect Memory",
  "category": "cognitive",
  "effects": {
    "memory_recall_boost": 2.0,
    "memory_decay_reduction": 0.0,
    "max_importance_cap": null
  }
}
```

```json
{
  "name": "Poor Memory",
  "category": "cognitive",
  "effects": {
    "memory_recall_boost": 0.5,
    "memory_decay_per_tick": 0.02,
    "max_importance_cap": 6
  }
}
```

`AgentMind.recall()` reads these effects before ranking. `Poor Memory` both
reduces recall chance and caps the importance of memories that can surface.

## Memory decay

Add `memory_decay_per_tick` to `engine/tick_manager.py` player update loop.
For each memory in `player.memories`:

- If `source == "preconceived"`: no decay unless the agent personally
  experiences a contradiction.
- If `source == "background"`: decay is halved; the structured event log
  remains regardless.
- Apply `memory_decay_per_tick` from traits to `memory["salience"]`.
- When `salience <= 0`: remove from `player.memories`, but keep a compressed
  summary in `player.compressed_memories` if `importance >= 7`.

## Files

- `engine/agent_memory.py` (new)
- `engine/traits.py` (add cognitive traits)
- `engine/tick_manager.py` (add memory decay pass)
- `data/library/traits/*.json` (new trait files)
- `docs/virtualWorld/Systems/Memory System.md` (new)

## Scenario authoring contract

A scenario author adds preconceived knowledge by writing the six keys above
into a player or character template. No code changes are needed beyond the
bootstrap loader in `AgentMind.load_preconceived()`. The keys are optional;
absence means "blank slate."

## Verification

- Load a scenario with preconceived knowledge. Verify the agent's first active
  prompt includes the injected memory and can name the known area/way.
- Starve a preconceived-knowledge agent. Verify `recall()` surfaces the food
  memory and the route to it, and that a `Poor Memory` agent has a lower
  recall chance.
- Run task-399 background simulation. Verify `consolidation_summary()` returns
  a bounded string that `Player.add_memory()` accepts unchanged.
- Save/load a character with preconceived memories, known ways, and
  investigation statuses. Verify they round-trip through
  `engine/serialization.py`.
- Run `python tools/lint_library.py` — trait files must validate.

## Non-goals

- A full world-knowledge graph or ontology.
- Automatic generation of preconceived knowledge from world topology.
- Replacing `VectorStore` or `SpatialMemory` with a single backend.
