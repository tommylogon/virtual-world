---
type: task
status: review
area: characters
priority: high
---

# task-403: Unified agent memory and knowledge system

**Filed:** 2026-09-17  
**Depends on:** task-324 (domain tags feed population queries), task-399
(background simulation needs memory consolidation)

## Progress

**Slice 1 — observation memories (done, 2026-09-21).** The prerequisite
task-425 was blocked on (`entity_ids` populated — was 0/17 — plus a per-subject
index) now exists:

- `engine/observation.py` records one **live observation memory per subject**:
  the area the character stands in and each item it can see there. Perception is
  not re-implemented — it reuses `engine/room_perception` (the shared
  prompt/panel source of truth), and the area itself is recorded
  unconditionally while its *contents* need light
  (`can_perceive`: dead/unconscious/asleep see nothing, darkvision counts).

  **People are deliberately not observed here** (changed 2026-09-21, task-434): a
  character is claimed by `Player.register_first_meeting`, which is also what
  pays for meeting them. If arrival stamped them too, the meeting grant would read
  a tick this had just refreshed and pay nothing — and paying on *sight* saturated
  Entertainment, because a crowded camp re-observes five to ten people on every
  arrival and they go stale again within the novelty window.
- `Player.record_observation` refreshes that memory **in place** rather than
  appending, so the store is bounded by *subjects*, not by visits. Measured:
  **908 memories after 10,080 ticks (1 min/tick) vs 912 after 672 ticks
  (15 min/tick)** — fifteen times the game time, the same number of memories.
- `Player.memory_index` (`subject_id -> memory_id`) takes "which memory is about
  this subject?" out of the memory list entirely, so it does not have to be found
  by scanning for a matching `entity_ids` entry. `has_seen` /
  `observation_tick` / `supersede_observation` read it; `observation_memory`
  returns `None` and falls back to a scan when the index has no usable entry, and
  the scan **repairs** the index — so the index can never silently disagree with
  the store. (Resolving the id back to the entry is still one pass; that is
  cheap next to the subject scan it removes, and a second id→entry map would be
  another structure to keep in sync with three writers.)
- `add_memory` now accepts `entity_ids` / `location` / `salience` and returns
  the entry; the index, `superseded_by` and an evicted subject's index entry all
  round-trip (`engine/serialization.py`) and are rebuilt on load.
- `superseded_by` retires a belief that was replaced (the bread was eaten) so
  recall stops surfacing it. Sightings *refresh*; they do not chain.
- Wired: on area entry (`engine/movement.py`, which the background tier also
  passes through — `_travel_toward` swaps `gs.active_player`) and once per
  character at load, since nothing is observed without a move and the starting
  area must not be the one place a character can never remember.
- Cost: **~5%** of a background week (measured by alternating A/B with warm-up;
  cProfile agrees). A first measurement of 43% was a cold-start artifact — the
  first run paid import/parse costs.
- Tests: `tests/test_observation_memory.py` (14), plus round-trip and load-time
  cases in `tests/test_serialization.py`. Soak unchanged: 23/23 alive, vitals
  identical to baseline at 1 and 15 min/tick.

Still open below (the `AgentMind` facade, preconceived knowledge, need-driven
retrieval, memory traits, memory decay).

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

- `engine/agent_memory.py` (new — the `AgentMind` facade; still to do)
- `engine/observation.py` (new — slice 1: perception → observation memories)
- `player.py` (slice 1: `memory_index`, `record_observation`,
  `observation_memory`, `observation_tick`, `has_seen`,
  `supersede_observation`, `add_memory` entity_ids/location/salience)
- `engine/movement.py` (slice 1: observe on area entry)
- `engine/serialization.py` (slice 1: `memory_index` + `superseded_by`
  round-trip, index rebuild, load-time perception pass)
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

## Progress — 2026-09-24 (slice 2: AgentMind)

`engine/agent_memory.py` (new) lands the facade and the three missing pieces.
It stores nothing itself — it delegates to `player.memories`, `player.known`,
`player.known_way_aspects`, `player.memory_index` and `engine/promotion.py`.

- **`AgentMind(player, graph, game_state, vector_store)`** — `recall(query, need,
  context, limit)` (tag/keyword match, ranked `importance * salience *
  recall_boost * urgency`, filtered by `max_importance_cap`), `remember(...)`,
  `know_area`/`knows_area`, `knows_way`, and `consolidation_summary(since_tick)`
  (delegates to `promotion.pending_span` + `promotion.summarize`).
- **Preconceived knowledge** — `load_preconceived(pdata)` injects authored
  `memories` (source `preconceived`), `known_areas`, `known_items` and
  `known_ways`. Idempotent by memory text. Wired into
  `engine/serialization._deserialize_player`, so a scenario or save carrying the
  keys bootstraps the character's knowledge; absent keys are a no-op.
- **Need-driven recall** — `surface_need_memory(need, tick, urgency, day_key)`
  recalls for a pressing need, writes one `source: need_recall` memory, and
  dedupes to once per in-game day per need. It never fabricates a location. Wired
  into `background_simulation._act` at the thirst and hunger thresholds (memory
  only — it cannot change an action).
- **Memory traits + decay** — `perfect_memory` (recall ×2, no decay) and
  `poor_memory` (recall ×0.5, `memory_decay_per_tick` 0.02, importance cap 6)
  added to `TRAIT_DEFINITIONS` with the new effect keys
  (`memory_recall_boost`, `memory_decay_per_tick`, `memory_decay_reduction`,
  `max_importance_cap`). `AgentMind.apply_decay()` fades salience and removes
  exhausted memories, is **inert without a decay trait**, never decays
  `preconceived` memories, fades `background` memories at half rate, and keeps
  `player.memory_index` consistent on removal. Wired into the per-player
  `tick_turn` loop, guarded by the trait so default behaviour is unchanged.

Tests: `tests/test_agent_memory.py` (13) — injection + idempotence, recall
match/rank/no-match, the poor-memory cap, once-per-day need recall (no
fabrication), decay inertness/removal/preconceived immunity, and a
preconceived-knowledge world load. Related suites
(background/serialization/promotion/traits/soak) all pass.
