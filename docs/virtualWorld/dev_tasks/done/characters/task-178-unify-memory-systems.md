---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Memory System]]"
---

# Task 178: Unify Character Memory Into One Backend System

## Status

**Filed**: 2026-08-04
**Priority**: High
**Status**: Done — verified 2026-08-04. 481 tests pass. All four systems unified into
`Player.memories[]`; dead code deleted; verified live with the Valerius scenario (Lyrie run
produced one clean `reaction` memory per turn with LLM-chosen importance + `entity_ids`).

## Problem

Character memory is fragmented across **four** parallel systems, three of which
duplicate each other and two of which are effectively dead:

| # | System | Where | Status |
|---|--------|-------|--------|
| 1 | `Player.memories` (structured list, CRUD via `/api/players/<name>/memories*`) | backend | **keep as canonical store** |
| 2 | `AgentMemory` (`player._memory` kv + `_plan`, `engine/agent_memory.py`) | backend | **dead — zero live callers** (only delegators + `__init__` import) |
| 3 | `MemoryStore` (`static/js/memory-store.js`, embeddings + cosine retrieval) | **browser localStorage** | **delete** — the agent's real recall work lives in per-browser localStorage |
| 4 | `EntityIndex` (`static/js/entity-index.js` → synced as `Player.knowledge`) | browser + backend field | **delete** — spatial half already exists backend-side, backend sync is write-only junk |

### Confirmed facts from the audit

- **System 2 is dead code.** `remember/recall/plan/recall_all` are delegated by
  `virtual_world_engine.py:484-495` but nothing calls those delegates anywhere
  in the tree (routes, API, or frontend). Delete it; a "fact" is just a memory
  with `type: "fact"`.
- **System 3 does the real agent recall** — thoughts, speech, actions, emotes,
  observations, reactions are all stored via `memory-manager.storeMemory` →
  `MemoryStore` → `localStorage["memories_<char>"]`, retrieved by
  `prompt-builder.js:239-246` with cosine + keyword + importance + recency +
  entity boost. It survives refresh but is per-browser, invisible, and its
  embeddings regenerate every page load.
- **System 4's spatial half already exists on the backend** (task-136):
  `Player.visited_areas` (movement.py:231), `Player.discovered_items`
  (item_actions.py:60), `Player.discovered_exits` (narration.py:319) — all
  persisted (`serialization.py:446-447`). The EntityIndex re-invented a worse,
  browser-local copy of this, and its `extractEntities` regex (`entity-index.js:197-205`)
  treated any word after "the/a/an" as an item → junk like
  `items: ["object","proud","tester"]`.
- **`Player.knowledge` is write-only.** `memory-manager.js:161-171` syncs the
  EntityIndex there; nothing server-side reads it, the frontend restores from
  localStorage instead. Pure dead weight in save files.
- **`Player.world_knowledge` is a duplicate of `reflection` memories.**
  `memory-manager.reflect()` (`memory-manager.js:30-81`) adds each LLM insight
  as a `reflection` memory (importance 8) AND appends it to `world_knowledge`
  (capped at 50 lines). Same content twice. Delete the blob, keep the memories.
- **🌍 World Lore (`world_lore`) is a separate world-level system — NOT touched.**
  Shared structured lore (`virtual_world_engine.py:93-94`), CRUD via
  `/api/world/lore*` (`routes/world_lore.py`), injected into every prompt as
  `=== WORLD LORE (common knowledge) ===` (`prompt-builder.js:448-452`).
- **MCP memory tools are developer/tooling access, not in-world agent memory.**
  `mcp_server.py:309-349` CRUDs `Player.memories` via `_api()`. Keep them,
  pointing at the same unified store — no change beyond the schema.

## Target State

```
Player.memories[]          ← THE ONE store (Sys 1 + Sys 3 + reflection), richer schema
Player.visited_areas       ← keep (task-136) — powers KNOWN ROUTES
Player.discovered_items    ← keep (task-136) — "saw item X in area Y" recall
Player.discovered_exits    ← keep (task-136)
Player.world_lore          ← UNTOUCHED (world-level, not per-character)
Player.world_knowledge     ← DELETE (duplicate of reflection memories)
Player._memory             ← DELETE (Sys 2, dead)
Player.knowledge           ← DELETE (write-only EntityIndex junk)
static/js/memory-store.js  ← DELETE
static/js/entity-index.js  ← DELETE
localStorage memories_* / entity_index_* keys ← gone (reset-scenario already clears; start fresh)
```

## Memory Schema (merged)

```json
{
  "id": "mem_...",
  "text": "...",
  "type": "observation|action|speech|thought|reflection|reaction|emote|location|...",
  "tick": 128,
  "timestamp": 1750000000,
  "importance": 4,
  "location": "Kitchen",
  "entity_ids": ["item_brass_key", "area_study"],
  "embedding": [0.12, ...],
  "tags": [],
  "source": "auto|manual"
}
```

Serialization already round-trips `memories` (`serialization.py:58,176-181`).
`entity_ids` is the "saw item X in area 2" mechanism (port of the
`memStore.add(..., entity_ids)` calls at `agent-engine.js:365,388,455`).

## Rich Memories (task-124) — flows into the unified store automatically

The "🖋️ Rich Memories" toggle (`config.richMemories`, `config.js:33`,
`index.html:255`) is **part of System 3**, not a separate system — it only
controls *how* an observation is generated, not *where* it's stored.

Flow today (`agent-engine.js`):
1. On area change (`:191-202`): if `config.richMemories`, call
   `_generateRichObservation()` — an async fire-and-forget LLM call
   (`:476-490`) that writes a first-person narrative observation.
2. It stores via `AgentMemory.storeMemory(..., 'observation')` →
   `MemoryStore` → **localStorage**.
3. Template mode stores the fast, past-tense snapshot instead (also
   `observation` type, same store).

**Unification impact:** none on the feature itself — once `storeMemory` POSTs
to the backend, rich and template observations both land in
`Player.memories` as `type: "observation"` with `source: "auto"`. The toggle
keeps working untouched. Only change: `_generateRichObservation` should
optionally attach `entity_ids` from `extractEntities` (it currently doesn't —
rich observations lose the entity links that template reactions get at
`agent-engine.js:365,388,455`).

## Changes

### Backend

- `engine/serialization.py` — delete `memory` (`:51`, `:166-168`),
  `knowledge` (`:60`, `:183`), `world_knowledge` (`:59`, `:182`). Add
  `embedding`/`entity_ids`/`source` to the memories round-trip.
- `routes/memories.py` — add:
  - `POST /api/players/<name>/memories/retrieve` — cosine + keyword +
    importance + recency + entity-boost (port of `memory-store.js:106-155`)
  - `POST /api/players/<name>/memories/reflect` — LLM summarize importance ≥ 6
    → `reflection` memories only (no `world_knowledge` write)
  - existing CRUD unchanged
- `engine/spatial_memory.py` (new) — BFS over the real graph seeded from
  `visited_areas`, emitting the `=== KNOWN ROUTES FROM HERE ===` block
  (replaces `entity-index.js:169-187` `buildSpatialContext`). Reads graph
  directly → no extraction, no junk.
- `engine/agent_memory.py` — delete. Remove `__init__` export
  (`engine/__init__.py:10`) and `virtual_world_engine.py:30,117,482-495`
  delegators.
- No new discovery tracking — `visited_areas`/`discovered_items`/
  `discovered_exits` already feed Entertainment novelty; `KNOWN ROUTES` just
  reads `visited_areas`.

### Frontend

- `static/js/agent/memory-manager.js` — `storeMemory` POSTs to backend
  (embedding computed server-side); `reflect` calls the reflect endpoint;
  delete `updateEntityIndex`/`syncEntityIndex` and the `world_knowledge`
  append (`:69-74`).
- `static/js/agent-engine.js` — `_generateRichObservation` (`:476-490`)
  optionally extracts `entity_ids` and passes them to `storeMemory` (rich
  observations currently lack entity links). Rich Memories toggle logic
  (`:191-202`) unchanged.
- `static/js/agent/prompt-builder.js` — `buildMemoryContext` (`:202-408`)
  retrieves from backend; spatial block (`:207-214`) calls the new spatial
  endpoint. Preserve: `=== I REMEMBER ===`, `=== KNOWN ROUTES ===`,
  `=== MY INVESTIGATION NOTES ===`, repeat-failure warnings, "what I haven't
  done" (all read `player.memories`, now the merged list).
- Delete `static/js/memory-store.js`, `static/js/entity-index.js`, the
  `getMemoryStore` global (`memory-store.js:272-283`), `VW.entityIndex` wiring
  (`main.js:50-58`), localStorage persistence, and the `memories_*` clear block
  in `saveload-view.js:217-223` (restart-scenario already wipes — start fresh).
- Remove `world_knowledge` reads: `plan-manager.js:54`, `memory-view.js:168,178`,
  `agent-view.js:988,1061`, `library-browser.js:438,486,549`.
- `static/js/inspector/agent-view.js` char-card export (`:1036-1044`) reads the
  merged list.

### Tests

- New `tests/test_spatial_memory.py` — routes built from `visited_areas` + graph.
- Extend memory route + serialization tests for `embedding`/`entity_ids`/`source`.
- Verify Entertainment-novelty tests still pass (discovery system untouched).
- Full suite: `python -m pytest tests/ -q -k "not mcp and not emote"`.

## Verification

- [x] No `_memory` / `knowledge` / `world_knowledge` remains in `.py` or `.js`
- [x] `memory-store.js` and `entity-index.js` deleted, no dangling references
- [x] Agent prompt still shows I REMEMBER / KNOWN ROUTES / INVESTIGATION NOTES
- [x] Bio Memories tab + MCP memory tools work against the unified list
- [x] Reflection writes `reflection` memories (no world_knowledge blob)
- [x] Rich Memories toggle still generates narrative observations into the unified store
- [x] Full pytest suite passes

## Implementation Notes (completed 2026-08-04)

- Backend: `engine/agent_memory.py` deleted; `engine/spatial_memory.py` added;
  `serialization.py` drops `_memory`/`knowledge`/`world_knowledge`, memories now
  round-trip `entity_ids`/`source`. `routes/players.py` `/knowledge` GET/PUT
  removed; `mcp_server.py` knowledge tools removed.
- `visited_areas` stores **area names** (`movement.py:231`), not node ids —
  `SpatialMemory.build_known_routes` matches on names.
- Reflect stays frontend-driven (LLM is browser-side per task-99): `reflect()`
  fetches memories from backend, LLM summarizes, POSTs insights to
  `/memories/reflect` which stores `type=reflection, importance=8`.
- `storeMemory` is now fire-and-forget POST to `/memories/entry`; entity_ids are
  the current area node id (`agent-engine._currentAreaEntityId`).
- `app.py` autosave hook now skips in TESTING mode (prevents tests polluting
  `data/autosave.json`). New tests: `test_memory_api.py` (5), `test_spatial_memory.py` (6).
- Full suite: 472 passed, 1 skipped (461 pre-existing + 11 new).
