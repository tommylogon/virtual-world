---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Memory System]]"
---
# Vector Embeddings & RAG Preparation

## Superseded by (2026-08-29)

The concrete RAG architecture proposed here was NOT adopted; the shipped design diverged:

| This doc proposed | What actually shipped |
|-------------------|-----------------------|
| Two-tier stores (world_lore + per-character) | ONE store `Player.memories[]` (task-178); world_lore is a separate world-level prompt block, not embedded |
| Embed `content` field | Field is `text` (`content` doesn't exist) |
| Tag convention `character:`/`room:`/`action:`/`item:` | Tags are single-word concepts only; entities live in a separate `entity_ids` array |
| FAISS in-memory index (recommended) | No-dependency JSON `data/embeddings.json` + pure-python brute-force cosine |
| `GET /api/memories/export` for bulk index build | Not built — moot, embeddings are generated incrementally per-memory browser-side |
| `embedding_hash` cache column | Not built — vector store keys by `<char>::<memory_id>`, so identity/dedup is free |
| EntityIndex-driven BFS for KNOWN ROUTES | EntityIndex deleted; spatial comes from `engine/spatial_memory.py` (task-136/task-178) |

---



**Filed**: 2026-07-16 (updated 2026-07-20)
**Priority**: Low (future)
**Status**: Superseded (moved 2026-08-29) — this was a *preparation* doc, never meant to
implement embeddings. The intent is now fully covered by [[task-91 — activate cosine
similarity in MemoryStore|task-91]] (embeddings are live). Remaining prep items were
dropped as unnecessary rather than left outstanding (see "Superseded by" below). Kept
as a historical record only.

---

## Summary

Prepare the memory and lore systems for future vector-embedding-based retrieval (RAG). Do **not** implement embeddings yet — this doc describes what the data model needs to support and the architectural decisions to make now so the RAG path is smooth later.

---

## Current Data Model (to be built by `proper_memory_editor.md`)

### World Lore entries
```python
{
  "id": "lore_001",
  "title": "The Kingdom of Rocheveron",
  "content": "The kingdom of Rocheveron is in the north, ruled by King Aldric...",
  "category": "geography",
  "tick_created": 0,
  "importance": 4,
  "tags": ["location:Rocheveron", "character:King_Aldric"],
  "source": "manual"
}
```

### Per-Character Memories
```python
{
  "id": "mem_001",
  "type": "observation",
  "tick": 42,
  "timestamp": "Day 1, 14:30",
  "content": "Tommy was in the Kitchen cooking eggs.",
  "location": "Kitchen",
  "importance": 3,
  "tags": ["character:Tommy", "room:Kitchen", "action:cooking"],
  "source": "auto"
}
```

### Shared Fields Compatible with Embedding
Both have:
- `id` — unique identifier
- `content` — the text to embed
- `importance` — weighting for retrieval scoring
- `tags` — metadata for filtered retrieval

---

## RAG Architecture (Future)

### Components Needed

1. **Embedding model** — calls an OpenAI-compatible API (same LLM endpoint or a dedicated embedding model like `text-embedding-3-small`)
2. **Vector index** — in-memory or file-based (FAISS, Chroma, or a simple numpy-based index) since this is a single-user desktop app with no server-side persistence requirement
3. **Retrieval pipeline** — on prompt build, embed the current context, query the index, return top-K matches
4. **Hybrid scoring** — combine vector similarity + importance + recency for ranking

### Data Flow

```
Character prompt assembly (_buildMemoryContext):
  1. Embed current room description + recent events → query vector
  2. Search world_lore index → top 3 lore entries
  3. Search character memories index → top 5 memories
  4. Merge results, format into prompt
```

### Storage Strategy (Choices)

| Approach | Pro | Con | Recommended? |
|----------|-----|-----|-------------|
| **In-memory FAISS index** | Fast, no dependencies | Rebuilt on reload, memory use | ✅ Yes |
| **SQLite + sqlite-vec** | Persistent, queryable | Dependency, complexity | Maybe later |
| **File-based numpy + pickle** | Simple, zero dependencies | No incremental updates | Fallback |
| **External vector DB (Chroma/Pinecone)** | Feature-rich | Overkill for single-user | No |

### Embedding calls

Estimate ~5 embedding calls per tick (1 for query + 3 for each character's memory search):
- Use the same OpenAI-compatible endpoint as the LLM
- Cache embeddings for unchanged entries (hash the content, skip re-embed if same)
- Batch embedding calls where possible

---

## Preparation Work (Do Now — No Embedding Code)

These changes make the RAG path smooth without implementing anything AI-embedding related:

### 1. Unique IDs on every entry

✅ Already covered — both lore and memory entries have `id` fields.

### 2. Content field is the canonical text to embed

✅ `content` field exists on both. Keep it clean — no markdown, no formatting, just plain text for the embedding target.

### 3. Tags as structured metadata

✅ Tags are simple strings. For RAG, add a convention:
- `character:<name>` — entity references
- `room:<name>` — location references
- `action:<verb>` — action type references
- `item:<name>` — item references

This allows filtered retrieval (e.g., "only memories involving Tommy").

### 4. Importance as a retrieval multiplier

The `importance` field (1-5) should be available as a scoring multiplier during vector search. No code needed now, just ensure it's stored.

### 5. API endpoint for batch export

Add one endpoint (not urgent):
- `GET /api/memories/export` — returns all lore + all character memories as JSON
- Used by the future embedding pipeline to build the initial index

### 6. Embedding hash cache column

Add an optional `embedding_hash` field to both entry types:

```python
"embedding_hash": None  # md5 of content; set to None initially
```

When RAG is implemented, the system checksums the content, compares to `embedding_hash`, and only re-embeds changed entries. This field can be added now with a default `None` and ignored until needed.

---

## When Ready to Implement

1. Choose an embedding model (start with the same LLM provider's embedding endpoint)
2. Add `embedding_cache.py` — handles embedding calls + hash-based caching
3. Add `vector_index.py` — wraps FAISS or numpy-based index with add/search/delete
4. Add `GET /api/memories/search?q=<text>` — for testing retrieval quality
5. Hook into `_buildMemoryContext()` in `agent-engine.js`
6. Add embedding progress UI (toast: "Indexing memories...")

---

## Open Questions

- Should world lore be embedded once globally, or re-embedded per-character context?
- Should we support cross-character memory search (Tommy remembers something about Miki)?
- How large can the total index grow before performance degrades? Estimate ~1000 entries max for a single scenario.
- Should we provide a "test retrieval" button in the inspector to debug what the RAG would return?
