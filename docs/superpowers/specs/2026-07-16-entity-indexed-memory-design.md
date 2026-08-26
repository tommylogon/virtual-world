# Entity-Indexed Memory System

> ⚠️ **SUPERSEDED (task-178, 2026-08-04).** The EntityIndex / MemoryStore / `world_knowledge`
> described in this doc were **deleted** in the memory unification. Memory is now ONE store,
> `Player.memories[]`, on the backend; the agent writes one LLM-generated `reaction` memory
> per turn via the react prompt's `memory` field. Spatial recall (the "KNOWN ROUTES" block)
> now comes from `engine/spatial_memory.py` (BFS over `visited_areas` + the real graph).
> See `docs/virtualWorld/AI & Narration/Memory System.md` and
> `docs/virtualWorld/dev_tasks/done/characters/task-178-unify-memory-systems.md`. This doc is
> kept as a historical record only.

## Problem

Characters repeatedly "re-discover" the same information (the fireplace is cold, the painting shows the Valerius family) because the memory system stores raw action logs instead of entity-linked subjective takeaways. There is no persistence of *known facts* — every turn the LLM sees the room from scratch.

## Architecture: Two-Tier Memory

### Tier 1: Entity Index (persistent knowledge)

Every room, item, exit, and notable entity the character encounters gets an entry in `CharacterEntityIndex`. Entries do **not** decay.

```
EntityIndexEntry {
  entity_id: string,         // e.g. "room:living_area", "item:fireplace"
  type: "room" | "item" | "door" | "player" | "concept",
  properties: {
    exits?: string[],        // room: ["kitchen via swinging door"]
    items?: string[],        // room: ["fireplace", "painting"]
    states?: string[],       // entity-level: ["cold and dark", "has ash"]
    interactions?: string[], // item: ["examined", "tried to light"]
    location?: string,       // item: "Living Area"
    last_seen_tick: number,
    visited_count: number,   // areas only
  },
  memory_ids: string[],      // references into episodic store
}
```

#### Storage

The entity index lives on the **frontend** (in-memory, persisted to localStorage) and on the **backend** (serialized on the Player object, saved/loaded with game state).

On every action result:
1. Parse the action and result text for entity names (areas, items, exits)
2. Extract state information ("cold", "dark", "contains X", "leads to Y")
3. Create or update entity index entries
4. Link new episodic memories to entity IDs

### Tier 2: Episodic Memory Store

Each action produces **two** memory records:

1. **Raw memory** — the action + result text, entity-linked, importance based on action type
2. **Subjective memory** — the character's inner monologue from the reaction phase, entity-linked, importance +1

```
EpisodicMemory {
  id: string,
  text: string,              // the subjective interpretation or raw log
  subjective: boolean,       // true if from reaction-phase inner monologue
  type: "discovery" | "observation" | "action" | "conversation" | "reflection",
  tick: number,
  room: string,
  entity_ids: string[],      // ["room:living_area", "item:fireplace"]
  importance: number,        // 1-10
  embedding: number[],       // 768-dim vector (client-side only)
  decay: number,             // 0 = fresh, incremented over time
}
```

#### Memory Decay

- Importance drifts down by ~1 per 50 ticks for episodic memories
- Below importance 2: only retrievable with very high vector similarity
- Entity index: **no decay** (known facts persist)
- Frequently retrieved memories decay slower (reinforcement via recency boost)

## Spatial Reasoning

The entity index builds a local map from areas the character has visited:

```
guest_bedroom → upstairs hallway
upstairs_hallway → guest bedroom, living room
living_area → kitchen, study, upstairs hallway, front door
kitchen → living room, cellar
```

When the LLM needs to decide where to go, BFS over the character's known connections computes reachable destinations. The result is injected as:

```
=== KNOWN ROUTES FROM HERE ===
Kitchen (has water, kindling, bread): go Upstairs Hallway → downstairs to Living Area → through swinging door
```

If the character has no goal, only adjacent areas with notable properties are shown.

## Retrieval & Prompt Injection

The decision prompt gets three memory sections:

1. **KNOWN FROM HERE** — entity index properties for current room + BFS routes to interesting places
2. **I REMEMBER** — top 3-5 episodic memories via hybrid search:
   - Vector similarity (semantic match to current context)
   - Entity overlap (memories linked to entities in current room / recent thought)
   - Importance × recency boost
3. **RECENT** — the last 2 raw actions (for immediate context only)

Memory context is injected into **observation** (spatial only) and **decision** (spatial + episodic) prompts. Not in reaction or system prompts.

## Data Flow

```
Action → Engine returns result
  → Store raw memory (entity-linked, importance=3-6 based on action type)
  → Extract entities from action + result → update entity index
  → Reaction phase: LLM generates inner monologue
  → Store subjective memory (entity-linked, importance = raw_importance + 1)
  → Next turn: build context from entity index + episodic RAG → LLM prompt
```

## Implementation Order

1. **EntityIndex class** (client-side, memory-store.js or new entity-index.js)
   - Schema, CRUD, persistence to localStorage + server sync
   - Entity extraction from action text
   - BFS route finding
2. **Backend entity index** (Player model + engine)
   - Add `knowledge` dict to Player
   - Add API endpoints for CRUD
   - Serialize/deserialize in to_dict/load_from_dict
3. **Modified memory storage in agent-engine.js**
   - Store raw + subjective memories with entity links
   - Create entity entries on action results
4. **Modified _buildMemoryContext**
   - Replace flat "RECENT EVENTS" with entity-indexed spatial + episodic sections
   - Hybrid retrieval scoring
5. **Memory decay** (background tick processing)
6. **Cleanup** — remove old redundant systems (world_knowledge, legacy _memory, duplicate MemoryStore storage)
