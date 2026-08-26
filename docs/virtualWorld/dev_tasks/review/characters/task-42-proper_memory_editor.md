---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Memory System]]"
---

# Proper Memory Editor + World Lore

**Filed**: 2026-07-15 (updated 2026-07-16)
**Priority**: High
**Status**: In Review — implemented (code-verified 2026-08-11). World lore CRUD in `routes/world_lore.py` + `static/js/inspector/lore-view.js`, lore injected via `system-prompt.js:28`; unified per-character memory system (task-178).

---

## Summary

Replace the single-textarea memory system with two complementary list-based systems:

1. **World Lore (shared knowledge)** — a list of structured lore entries that every character sees as common knowledge.
2. **Per-Character Memory (structured list)** — individual memories with type, tick, location, importance, tags. Editable per character.

Both systems use the same underlying list structure so they can be unified for future RAG/embedding support (see `vector_embeddings_rag_prep.md`).

---

## Part 1: World Lore (List-Based Shared Knowledge)

### Concept

A list of structured lore entries stored at the world level. Every character sees them in their system prompt as "common knowledge everyone in this world knows." Not a flat text blob — individual entries with titles, categories, and metadata.

### Lore Entry Structure

```python
{
  "id": "lore_001",
  "title": "The Kingdom of Rocheveron",
  "content": "The kingdom of Rocheveron is in the north, ruled by King Aldric...",
  "category": "geography",    # geography, history,人物, factions, magic, religion, etc.
  "tick_created": 0,
  "importance": 4,            # 1-5, controls prominence in prompt
  "tags": ["location:Rocheveron", "character:King_Aldric"],
  "source": "manual"          # "manual" or "auto_generated"
}
```

### Storage

New field on the `VirtualWorld` class, serialized in `world_template.json`:

```python
# virtual_world_engine.py
self.world_lore = [
    {"id": "lore_001", "title": "...", "content": "...", ...},
    {"id": "lore_002", ...},
]
```

### Prompt Injection

In `agent-engine.js:_buildCharacterSystemPrompt()`, inject world lore entries as formatted text:

```
=== WORLD LORE (common knowledge) ===
[Geography] The Kingdom of Rocheveron
  The kingdom of Rocheveron is in the north, ruled by King Aldric...

[History] The Great Fire of 1024
  A massive fire destroyed half the capital...

[Factions] The Iron Guild
  Merchants and smiths who control trade in the southern provinces...
```

Only include lore entries with importance >= threshold (configurable, default show all). Future: relevance filtering before RAG is built.

### Frontend

- **World tab** in the inspector panel (new section)
- List view of all lore entries (same visual pattern as per-character memories)
- [+ Add Lore Entry] button
- Per-entry: [✏️ Edit] [🗑 Delete]
- Entry editor modal: title, content (textarea), category (dropdown), importance (1-5 slider), tags (comma input)
- Save calls `/api/world/lore` (batch) or individual CRUD

### API

- `GET /api/world/lore` — returns `{ "lore": [...] }`
- `PUT /api/world/lore` — replaces entire lore list
- `POST /api/world/lore/entry` — add single entry
- `PUT /api/world/lore/entry/<id>` — update single entry
- `DELETE /api/world/lore/entry/<id>` — delete single entry
- Persisted in `world_template.json`: `{ "world_lore": [...], ... }`

### Auto-Propagation

World lore is injected into every character's system prompt server-side. No per-character copy needed. The prompt builder reads from `self.world_lore` directly.

---

## Part 2: Per-Character Memory (Structured List)

### Memory structure

Each memory is a structured entry:

```python
{
  "id": "mem_001",
  "type": "observation",  # observation, conversation, location, event, learned
  "tick": 42,
  "timestamp": "Day 1, 14:30",
  "content": "Tommy was in the Kitchen cooking eggs.",
  "location": "Kitchen",
  "importance": 3,  # 1-5, determines retention
  "tags": ["character:Tommy", "room:Kitchen", "action:cooking"],
  "source": "auto"  # "auto" or "manual"
}
```

### Location memory

Automatically record when a character moves to a new room:

```
You remember being in the Foyer at 08:00.
You moved to the Kitchen at 08:05.
You moved to the Garden at 08:15.
```

### Frontend editor

Replace the single textarea with a list view (same visual pattern as world lore):

```
🧠 Memories (24 total)
━━━━━━━━━━━━━━━━━━━━━━━━━

[+ Add Memory] [🗑 Clear All]

📌 Day 1, 14:30 — Observation
   "Tommy was in the Kitchen cooking eggs."
   📍 Kitchen | ⭐ Importance: 3 | 🏷️ character:Tommy
   [✏️ Edit] [🗑 Delete]

📌 Day 1, 14:00 — Location
   "Moved from Foyer to Kitchen."
   📍 Kitchen
   [✏️ Edit] [🗑 Delete]
```

### Memory filtering

- Filter by type (observations, conversations, locations, events)
- Filter by location
- Filter by character
- Search text
- Sort by tick or importance

### Backend

- Store memories as a JSON list in a new field `Player.memories`
- Add API for CRUD operations on individual memories
- Automatic memory creation on significant events (move, conversation, item acquisition, etc.)
- Memory consolidation/forgetting (old or low-importance memories are summarized and trimmed)

### Prompt Integration

In `_buildMemoryContext()`, combine both sources:

```
=== WORLD LORE (common knowledge) ===
{formatted lore entries}

=== RECENT EVENTS ===
{last 8 memories}

=== RELATED MEMORIES ===
{RAG-retrieved memories}
```

---

## Design Notes for Future RAG Compatibility

Both world lore entries and per-character memories share a compatible structure:
- `id`, `content` (the text), `importance`, `tags`
- Lore has `title` + `category`; memories have `type` + `tick` + `location`
- Both can be embedded and stored in a vector index
- Tags enable filtered retrieval (e.g., only lore tagged "location:Rocheveron")

See `vector_embeddings_rag_prep.md` for the future RAG integration plan.

---

## Files Affected

- `virtual_world_engine.py` — add `world_lore` list field, auto-memory on events
- `player.py` — add structured `memories` field
- `app.py` — world lore CRUD API + memory CRUD API endpoints
- `static/js/api.js` — API calls for both systems
- `static/js/inspector.js` — world lore list editor + memory list editor
- `static/js/agent-engine.js` — inject world lore + structured memories into prompt
- `world_template.json` — add `world_lore` top-level field (list)
- `static/css/style.css` — optional styling for list editors
