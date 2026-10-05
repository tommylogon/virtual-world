---
type: task
status: done
area: emotions
priority: medium
---

# task-505: Embedding bridge: resolve novel emotion/emote labels to affect dimensions

**Filed:** 2026-09-24
**Related:** task-350, task-96

## Goal

When an agent/game event declares a feeling or emote whose label is not in engine.emotion.LABEL_TO_DIM, resolve it semantically to the nearest affect dimension via the configured embedding provider (LM Studio, browser EmbeddingClient) and post {mapped:{dim:delta}} to /api/players/<name>/emotions/map, instead of the current graceful no-op. Keeps creative LLM vocabulary from being silently dropped, so events/decisions translate into the affect map and therefore select the correct expression portrait.

## Acceptance

- A novel emotion label declared by an agent or a game event lands on a real
  affect dimension instead of being dropped.
- A label that genuinely resolves to nothing is still a graceful no-op.
- The keyword map stays the fast path and is never overridden.
- A world with no embedding provider pays nothing and breaks nothing.

## Implementation — 2026-09-28 (WT-C)

### What was already there

The **browser** half of this bridge was complete before this task:
`static/js/shared/emotion-mapper.js` resolves keyword → substring → embedding
against `DIM_ANCHORS`, and both callers (`prompt-builder/room-context.js:81`,
`prompt-builder/memory-context.js:114`) post the result as `{mapped:{dim:delta}}`
to `/api/players/<name>/emotions/map`. That is the "post {mapped:...}" half of
the goal, already working.

What was missing was the **server** half. `engine/emotion.py map_label` was
keyword-only, and `felt_from_llm` rejected anything that was not a `BASELINES`
key outright. So the goal's actual gap was: an emotion reaching the engine
without passing through the browser — a trigger effect, a background agenda, a
saved decision — had no semantic path at all.

### Files

- `engine/emotion.py` — `DIM_ANCHORS`, `resolve_label_semantic`,
  `semantic_labels_enabled`, `reset_anchor_cache`; `map_label` and
  `felt_from_llm` fall through to the semantic resolver.
- `engine/runtime_config.py` — the `emotion.semantic_labels` gate.
- `tests/test_emotion_semantic_bridge.py` — **new**, 24 tests.

`DIM_ANCHORS` mirrors the JS mapper phrase for phrase, and a test asserts every
anchor dimension exists in the JS file and in `BASELINES`, so the two cannot
drift into resolving the same label differently.

### The gate, and why it is off by default

The keyword map covers the authored vocabulary and costs a dict lookup. A
semantic miss costs an embedding call and, on a world with no embedding model,
a model-load attempt. So `emotion.semantic_labels` defaults to **false** and
`resolve_label_semantic` returns `None` before touching a provider. It is a
documented tunable with a Settings label, not a hidden default.

An injected `embed_fn` bypasses the gate deliberately: supplying an embedder is
itself the explicit choice. What the gate governs is *automatic* provider use.

### A real bug the existing tests caught

Wiring `felt_from_llm` to the full `map_label` broke
`tests/test_emotion.py::test_unknown_label_rejected` — and it was right to.
`map_label` substring-matches, and **"hangry" contains "angry"**, so a declared
feeling was being resolved by coincidence into an emotion the model never named.
That is precisely the "a creative LLM can't invent dimensions" guarantee the old
exact `label not in BASELINES` check was protecting.

`felt_from_llm` therefore uses `resolve_label_semantic` **only** — the semantic
bridge or nothing, never a coincidental substring. The recall path
(`/emotions/map`) keeps its pre-existing substring behaviour, which is fine
there: it is a recall heuristic over authored vocabulary, not a deliberate
declaration by a model. Both behaviours are pinned by tests.

### Failure handling

- `embeddings.embed` returns a **zero vector** when the model fails to load. A
  zero vector cosines to 0 against everything, so accepting it would silently
  resolve every unknown label to whichever dimension happened to be first.
  Zero vectors are rejected outright, and a mismatched anchor count is not
  trusted.
- The **default** provider's failure is remembered, so a world with no embedding
  model pays one attempt rather than one per label. A caller-supplied
  `embed_fn` is *not* memoised — its failures are the caller's to see again.
- Anchor vectors are embedded once and reused; `reset_anchor_cache()` clears
  them when the provider changes.

### Handed to WT-0

Nothing. No hub file was touched.

### Verify

`python -m pytest tests/ -q -k "emotion or affect"` — 91 tests. The new file
covers: the gate is off by default and never reaches the provider when off; the
keyword path wins over the embedder and a novel label falls through to it; a
distant label stays unresolved; resolution never invents a dimension; intensity
scaling and the explicit `max_intensity` still apply; malformed input is still
`None`; a raising embedder, a zero-vector embedder and a short anchor batch are
all non-fatal; the default provider is tried once and a caller's embedder is
retried; anchors are embedded once; and the "hangry"/"angry" coincidence is
rejected on the LLM path while still accepted on the recall path.
