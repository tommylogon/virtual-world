---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Memory System]]"
---
# Activate Cosine Similarity in MemoryStore

**Filed**: 2026-07-22
**Priority**: High
**Status**: In Review — implemented 2026-08-23 per the re-scope below. Settings →
🧬 Embedding tab (enable/url/model/dims/key/test), `static/js/shared/embedding-client.js`,
`engine/vector_store.py` (JSON store, pure-python cosine, atomic writes) + routes in
`routes/memories.py` (`POST /api/memory/embeddings` upsert, `/search`, `GET /stats`,
409 on dim conflict; memory clear also drops that character's vectors). Write path:
`AgentMemory.storeMemory()` embeds after successful store. Read path:
`buildMemoryContext()` embeds the query and merges top-5 hits ≥0.35 cosine into the
recall pool at 2×score weight, keyword scoring untouched as fallback. Verified: 11 new
tests in `tests/test_vector_store.py`, full suite 1066 passed, live curl round trip
(upsert→ranked search→conflict), settings UI renders + populates. Not yet verified with
a real embedding provider (Ollama/LM Studio) — needs a live endpoint E2E.

## New scope (2026-08-23)

1. **Settings → Embedding section**: enable toggle, Base URL (e.g.
   `http://localhost:11434/v1`), model name (`nomic-embed-text`,
   `text-embedding-3-small`, ...), dimensions (blank = auto-detect from first
   response), optional API key, Test button. Persisted in browser config (IndexedDB),
   same pattern as LLM connection settings. API keys never sent to backend.
2. **Embedding client** (`static/js/shared/embedding-client.js`): POST
   `{baseUrl}/embeddings`, batch input, dimension auto-detect, graceful null on any
   failure (system degrades to keyword-only recall).
3. **Lightweight vector store** (backend): `data/embeddings.json` keyed by
   `{character}|{memory key}`, pure-python cosine search — no new dependencies,
   no sentence-transformers. Endpoints in `routes/memories.py`:
   - `POST /api/memory/embeddings` — bulk upsert `{items: [{key, vector}]}`
   - `POST /api/memory/embeddings/search` — `{character, vector, k}` → top-k keys + scores
4. **Write path**: `AgentMemory.storeMemory()` embeds the memory text after a
   successful store and upserts the vector (fire-and-forget).
5. **Read path**: `buildMemoryContext()` embeds the recall query, searches, merges
   cosine-scored memories into the existing candidate pool (keyword scoring stays as
   fallback when embeddings are disabled/unavailable).
6. Legacy root-level `embeddings.py` / `/api/embeddings` (sentence-transformers) is
   superseded — removal tracked separately.

Prior art: `F:\AI\Aura\Diary` (rag_utils.py — query embedding → top-k similar events;
nomic-embed via local LM Studio endpoint).

## What to expect on your next run

**Event stream: nothing new appears** — both systems are silent by design. Silence =
working (or disabled; check Settings → 🧬 Embedding shows model + dims after Test).
Failure mode is invisible too: dead endpoint = silent keyword-only fallback, which is
why you Test Connection first. Ollama CORS gotcha: may need `OLLAMA_ORIGINS=*`.

**Behavioral fingerprint** — agents act on meaning-matched memories with zero word
overlap:
- *Taco Bell*: Miki's thought drifts to "tonight feels unfinished" → she returns to
  the booth unprompted (the hidden-object memory shares no keywords with her thought).
- *Mansion*: an agent in the study recalls the calling card found in the hall —
  cross-area resonance; the deduction chain should connect in fewer turns.

**In exports**: read `=== I REMEMBER ===` blocks in prompt echoes — memories listed
that share no vocabulary with their surroundings are semantic hits (they enter at
2× cosine weight).

**Not yet**: pre-existing memories have no vectors (only new ones embed); inspector-
added backstory and reflections bypass storeMemory (backfill = follow-up); recall is
per-character by design. If nothing happens after two runs with a green test,
tune the 0.35 threshold / 2× weight in `memory-context.js`.

---

## Summary

The embedding infrastructure exists (embedding generation, cache, `/api/embeddings` endpoint, `cosineSimilarity()`) but is **dormant** — the `retrieve()` method gives a flat `0.3` boost for any memory that has an embedding, instead of computing actual cosine similarity against the query.

This task activates semantic retrieval, making memory recall dramatically more relevant for agents.

---

## Evidence

`static/js/memory-store.js:96-145` — `retrieve()`:

```js
let simScore = 0;
if (m.embedding) {
    simScore = 0.3;  // flat boost, NOT cosine sim
}
```

The `cosineSimilarity()` static method at line 15 exists but is **never called**.

Compare humanoidagents `generative_agent.py:260-264`:
```python
query_embedding = self.LLM.get_embeddings(query)
scores = cosine_similarity([query_embedding], memory_item_embeddings)[0]
```

Also: `buildContext()` at line 149-177 generates a `queryEmbedding` but passes it as the third `entityBoost` parameter to `retrieve()` — so the query embedding is completely ignored during scoring.

---

## Changes

### 1. Fix `retrieve()` to accept and use query embedding for cosine similarity

Change signature from:
```js
retrieve(query, maxResults = 5, entityBoost = false)
```
to:
```js
retrieve(query, maxResults = 5, queryEmbedding = null, entityBoost = false)
```

In the scoring loop, when `queryEmbedding` AND `m.embedding` are both available, compute actual cosine similarity:
```js
if (queryEmbedding && m.embedding) {
    simScore = MemoryStore.cosineSimilarity(queryEmbedding, m.embedding);  // 0-1
}
```

Keep the flat `0.3` fallback when memory has an embedding but no query embedding was provided.

### 2. Update `buildContext()` call to `retrieve()`

Line 169 changes from:
```js
const mems = this.retrieve(query, maxResults, queryEmbedding);
```
The `queryEmbedding` param is currently consumed as `entityBoost`. Fix so it's passed as the proper `queryEmbedding` parameter, and `entityBoost` stays as its own arg.

### 3. Update all other callers of `retrieve()`

Check `prompt-builder.js:138` and any other places that call `retrieve()` — they should continue working with the new signature defaults.

### 4. (Optional) Backend `get_relevant_memories()` in `player.py:287-308`

Currently keyword-only. If the backend ever needs semantic retrieval, add the same fix — but this is lower priority since the frontend MemoryStore is what actually feeds agent prompts.

---

## Scoring After Fix

The retrieve scoring would become:

| Component | Weight | Description |
|-----------|--------|-------------|
| `simScore` | ×5 | Cosine similarity (0-1) between query and memory embedding |
| `kwScore` | ×3 | Keyword overlap ratio |
| `recencyBoost` | ×2 | Linear decay over 500 ticks |
| `importanceBoost` | ×2 | 0.1-1.0 scale |
| `entityBoost` | +2.0 | If entity_ids match current room |

This mirrors humanoidagents' approach but keeps all 5 signals instead of just 3.

---

## Test

1. Load a world with a character that has embedded memories
2. Call `MemoryStore.retrieve()` with a query that has semantic overlap with a memory but zero keyword overlap (e.g. query "rest" for a memory about "slept in the bedroom")
3. Verify the memory scores higher than without cosine sim
