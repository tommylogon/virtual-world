---
type: doc
tags: [system/memory, topic/memory-dynamics]
---

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
  "emotion": {"label": "afraid", "intensity": 6},
  "memory_emotions": [{"label": "embarrassed", "intensity": 4}, {"label": "aroused", "intensity": 7}],
  "salience_override": 0,
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
- `emotion` is the **primary** single emotion (backward-compatible with the engine spike path).
- `memory_emotions` is the **full list** of emotions attached to this memory
  (`[{label, intensity}]`) — the richer, multi-emotion form the editor/generator writes. Recall
  re-feels **all** of them, not just the primary.
- `salience_override` (0–10) is a manual recall-boost; >0 shows a **⚡ salience** badge.
- `tick` is the time the memory was created. A **negative** tick means *before the scenario
  started* — the editor's **"Turns before start"** field writes `tick = -N` to simulate a
  pre-scenario/seed memory.

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
- Tag chips (`#tag`) + emotion chips (from `memory_emotions`)
- Edit / delete per entry; Add + Clear All + **✨ Gen Memory** buttons
- Rich editor modal (sectioned cards matching the Settings styling):
  - **Content** (textarea), **Classification** (Type / Importance / Tick / **Turns before start**),
    **Context** (Source / Location / Salience / **Entity references**), **Emotions (multiple)**,
    **Tags**, **Semantic** (embedding status + generate).
  - **Entity references** is a searchable multi-select of area/item/character nodes → `entity_ids`.
  - **Emotions (multiple)** uses a curated, grouped vocabulary (Core / Warm-Social / Anxious /
    Arousal / Down / Calm / Determined / Jealous) **plus a free-text custom label input** — so any
    agent-invented label can be added. Each emotion has its own intensity (1–10) and remove (×).
  - **Turns before start** writes a negative `tick` to simulate a pre-scenario memory.
  - **💾 Save** writes `memory_emotions` (and the primary `emotion`), then auto-embeds the text.

### ✨ Memory Generator (first-person seed memories)

The **✨ Gen Memory** button opens a generator: describe the kind of memory (a food memory, a
nightmare, a dream, a secret…) and the LLM writes it **in the character's first-person voice** as a
**standalone seed** — explicitly *not* tied to the current scene, area, or scenario. It uses the
character's actual `personality` + `description` as the identity block. The drafted text is editable
before it's saved as a `source: manual` (SEED) memory and auto-embedded. See **Idea → Options →
Memory preview** sections in the modal.

## Memory emotion recall (residue)

When an emotionally-tagged memory surfaces, it re-feels a fraction of what it carried. Two paths:

1. **Self-recall** — `memory-context.js::_respikeFromMemories` fires while your own recall block is
   built; it re-feels every attached `memory_emotions` (affect map + subtle vital).
2. **Social recall** — `room-context.js::_fireSocialRecall` fires when another character *says
   something that touches one of your memories*; it re-feels it, and (when the speaker is a known
   person) also nudges your relationship toward them. An anonymized voice ("a woman's voice") still
   re-feels but attributes no relationship.

Both go through `POST /api/players/<name>/emotions/map`. See
[[Characters/Emotion & Affect System]] for the dimension map, semantic label mapping, vital
coupling, and relationship valence.

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

## Memory dynamics (task-685)

Memories are no longer static entries. Every memory carries optional dynamics
fields — `category` (episodic/semantic/procedural/social/belief), `activation`,
`confidence`, `reinforcements`, `last_recalled_tick`, `reflection_depth`,
`source_memory_ids`, `contradicts` — owned by `engine/memory_dynamics.py`:

- **Recall reinforces** — every retrieval path (the `/memories/retrieve`
  endpoint, `Player.get_relevant_memories`, `AgentMind.recall`, and the
  client's vector-search merge via `POST /memories/reinforce`) stamps
  bounded reinforcement instead of the old unbounded +1-importance ratchet.
- **Re-encounter reinforces** — a near-verbatim memory written days later
  strengthens the original instead of appending (extends the task-346 dedup).
- **Decay is non-uniform** — `activation` fades with per-memory resistance
  (importance ≥ 8, strong emotions, reinforcements, and concluded/semantic
  categories resist); unimportant faded memories are removed, important ones
  never are. Rate: the `memory_decay_per_tick` trait, or the
  `memory.decay_per_tick` config default (0.01; 0 freezes).
- **Reflection changes the character** — `reflect()` asks for structured
  insights (belief + confidence + optional emotional association, behaviour
  expectation, relationship delta) and stores them as depth-1 `belief` /
  `procedural` / `social` memories with `source_memory_ids` provenance;
  `rel:`/`dim:` tags feed the derive.py per-person profiles directly.
  Reflections of reflections are refused (depth guard, client and server).
- **Contradictions are marked, never resolved** — an assert/deny pair sharing
  an entity is linked in `contradicts[]` and the older side loses a little
  confidence; the prompt says "you are not sure".

Full design: [[Memory Dynamics]]. Status: implemented and wired
(endpoint + tick + prompt paths tested in `tests/test_memory_dynamics.py`),
including the interface: dynamics badges and a stats header in the inspector's
Memories tab, a Category/Confidence/Connections editor, and the full
**Memory Mind** dashboard (`static/js/inspector/mind-view.ts`, opened from the
🧠 Mind button — timeline, filters, connections, per-person derived profiles
via `GET /api/players/<name>/memories/people`).

## Related

- [[dev_tasks/done/characters/task-178-unify-memory-systems|task-178: Unify memory systems]]
- [[dev_tasks/done/prompting/task-160-parameterized-actions-in-prompts|task-160: Parameterized actions (LLM memory field)]]

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Read next** — [[Memory Dynamics#5. Query-driven retrieval]]

**Features** — [[memory|Memory]] (#22), [[memory-pipeline|Memory pipeline]] (#41)

**Dev tasks** — [[dev_tasks/cancelled/task-26-vector_embeddings_rag_prep|task]], [[dev_tasks/done/characters/task-178-unify-memory-systems|task]], [[dev_tasks/done/characters/task-37-memory_context_relative_time|task]], [[dev_tasks/done/characters/task-91-activate_cosine_similarity_retrieval|task]], [[dev_tasks/done/emotions/task-96-emotional_residue_intercharacter_memory|task]], [[dev_tasks/review/characters/task-42-proper_memory_editor|task]]

**Neighbouring notes** — [[Agent Engine]], [[LLM Providers]], [[Memory Dynamics]], [[Narration System]], [[Turn-Based System]]

<!-- connected:end -->
