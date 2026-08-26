# Memory System

VirtualWorld has a **single unified memory system**: every character's memories live in
`Player.memories[]` (a structured list on the backend) and are written/read through one API
and one editor. This replaced four parallel systems (backend kv-store, browser-localStorage
`MemoryStore`, `EntityIndex`, and `world_knowledge`) in **task-178**.

## The One Store

All memory lives in `Player.memories[]` — a list of entries. Serialization round-trips it
(`engine/serialization.py`). The memory editor, the agent engine, and the MCP memory tools all
operate on this same list.

### Memory schema

```json
{
  "id": "mem_...",
  "text": "subjective 1-3 sentence takeaway",
  "type": "observation|action|speech|thought|reflection|reaction|emote|location|...",
  "tick": 128,
  "timestamp": 1750000000,
  "importance": 7,
  "location": "Living Room",
  "entity_ids": ["area_living_room"],
  "embedding": null,
  "tags": ["valerius", "door"],
  "source": "auto|manual"
}
```

- `source` is `manual` for editor-added / seeded backstory (rendered with a **SEED** badge),
  `auto` for everything the agent generates at runtime.
- `tags` are **single-word conceptual categories** (fear, trust, mystery, amnesia) — not
  names, items, or places. `_sanitizeTags()` (`static/js/agent/memory-manager.js`) drops
  multi-word/hyphenated tags (`silent-stranger`) and any tag matching a known
  player/item/area name before storing. The LLM prompt instructs the same. New tags are
  auto-registered into the **tag library** (id-keyed files in `data/library/tags/`), so they
  dedupe naturally. See [[Library System/Tags System]].

## Who writes memories

| Writer | Where | Type |
|--------|-------|------|
| **Agent react phase** | `agent-engine.js` | `reaction` (LLM-generated subjective memory) |
| **Agent non-reactive phase** | `agent-engine.js` | `reaction` |
| **Wake from unconsciousness** | `agent-engine.js` | `thought` |
| **Memory editor** | `static/js/inspector/memory-view.js` | user-selected |
| **Seeds/backstory** | scenario files (`world_template.json`) | `observation` (`source: manual`) |
| **MCP memory tools** | `mcp_server.py` | user-selected |

### LLM-generated memories (task-178 / task-160)

The agent stores **one memory per turn** — a subjective takeaway the LLM writes in the react
phase, not raw action/room dumps. The react prompt asks for:

```json
{"memory": {"text": "...", "importance": 7, "tags": ["door"]}}
```

`_extractMemory()` (`agent-engine.js`) parses this (plain-string fallback → importance 5).
Speech, emotes, and inner monologues are logged to the event stream but **not** stored as
memories — people don't remember their own spoken lines.

## Memory API

`routes/memories.py`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/players/<name>/memories` | List all memories |
| PUT | `/api/players/<name>/memories` | Replace all memories |
| POST | `/api/players/<name>/memories/entry` | Add a memory entry |
| POST | `/api/players/<name>/memories/entry/<id>` | Update a memory entry |
| DELETE | `/api/players/<name>/memories/entry/<id>` | Delete a memory entry |
| POST | `/api/players/<name>/memories/clear` | Clear all memories |
| POST | `/api/players/<name>/memories/retrieve` | Score + return most relevant memories |
| POST | `/api/players/<name>/memories/reflect` | Store LLM insights as `reflection` memories |
| GET | `/api/players/<name>/memories/spatial` | KNOWN ROUTES block (BFS over `visited_areas`) |

## Frontend

### `static/js/agent/memory-manager.js`

`window.AgentMemory`:

- `storeMemory(charName, text, importance, type, tick, entity_ids, tags)` — POSTs to the
  backend `/memories/entry`. Fire-and-forget. Also registers any new tags into the library.
- `reflect(charName)` — fetches memories (importance ≥ 6), asks the LLM for 1-2 insights,
  POSTs them to `/memories/reflect` (stored as `type: reflection`, importance 8). Runs every
  5 turns in reactive mode. No `world_knowledge` blob anymore.

### `static/js/inspector/memory-view.js`

The inspector Memories tab renders `Player.memories[]` directly:

- Importance-colored left border (red ≥ 8, orange ≥ 6, green ≥ 4, grey otherwise)
- **SEED** badge for `source: manual`
- Tag chips (`#tag`)
- Edit / delete per entry; Add + Clear All buttons
- Editor modal uses the shared **`TagMultiselect`** component (searchable, create-on-the-fly)

## Spatial memory (separate, task-136)

`visited_areas`, `discovered_items`, `discovered_exits` are persisted on the player
(`serialization.py`) and power the `KNOWN ROUTES` prompt block via `engine/spatial_memory.py`
(BFS over the real graph, seeded from `visited_areas`). These are discovery state, not
memories — do not confuse them with `Player.memories[]`.

## What was deleted (task-178)

- `engine/agent_memory.py` (`AgentMemory` kv-store) — dead code, zero callers
- `static/js/memory-store.js` (browser localStorage embeddings) — the agent's real recall
  work lived invisibly per-browser
- `static/js/entity-index.js` (`VW.entityIndex`) — regex extractor producing junk entities
- `Player._memory`, `Player.knowledge`, `Player.world_knowledge` — dead/duplicate fields

## Context window management

`ContextWindowManager` (`static/js/context-window.js`) prunes the per-character conversation
history. AgentEngine config: `maxTokens: 9500, maxMessages: 30, recentTurnCount: 6`.

- History grows ~4 messages/turn (think-decide user+assistant, react user+assistant)
- Prune triggers >30 messages or >9500 tokens (~5-7 turns)
- Prune keeps: system message + last `recentTurnCount × 3` (18) messages; older turns
  replaced with `[Summary: N earlier turns omitted.]`
- **History is NOT reset per turn** — it persists across turns and is only cleared on
  `start()`/`reset()`. The LLM-generated `memory` field is the durable record once old
  messages get summarized away.

## Related

- [[dev_tasks/done/characters/task-178-unify-memory-systems|task-178: Unify memory systems]]
- [[dev_tasks/done/prompting/task-160-parameterized-actions-in-prompts|task-160: Parameterized actions (LLM memory field)]]
