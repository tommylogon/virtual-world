---
type: doc
tags: [system/memory, topic/memory-dynamics, topic/reflection, topic/retrieval]
---

# Memory Dynamics — from a memory list to an evolving internal model

> [!success] Status 2026-10-04 (task-685..691) — **implemented and wired**
> The engine arithmetic (`engine/memory_dynamics.py`), the write-path
> reinforcement and contradiction detection (both the engine and the HTTP write
> path), the tick decay/consolidation hook, the structured reflect endpoint +
> depth guard, the retrieval 2.0 scorer with structured grouping, the client's
> sectioned recall block, and the interface: inspector dynamics badges/stats/
> filters, the Category/Confidence/Connections editor, the per-person profiles
> endpoint + panel, and the full **Memory Mind** dashboard (`mind-view.ts`).
> All exercised by `tests/test_memory_dynamics.py` and verified live in the
> browser against a seeded scenario.
>
> [!caution] Still planned
> Consolidation beyond cap-pressure, and the reflection flow for NPC-only
> characters. See the open questions in the task tree.

VirtualWorld's memory system already has the right skeleton: one unified
`Player.memories[]`, LLM-written subjective takeaways, importance 1–10, tags,
entity links, emotions, embeddings, and periodic reflection. What it does not
have is **dynamics**: a memory is written once, scored statically, and never
changes again except by a manual edit.

This document describes the layer that turns stored memories into an evolving
internal model of the world. The design question for every feature below is the
same: **what does this memory do**, not what does it say.

```text
experience → encoding → memory → reinforcement/weakening → association
           → retrieval → interpretation → reflection → belief / expectation
           → changed behaviour
```

---

## 1. The two-axis model (type stays; category is added)

Today `type` conflates two things: the surface form of the encoding
(`observation`, `speech`, `thought`, `reaction`…) and, occasionally, the *kind*
of thing remembered (`reflection`, `backstory`). Surface form matters for UI
icons; kind matters for reasoning. They are separated:

| Axis | Field | Values | Written by |
|---|---|---|---|
| Surface form | `type` (unchanged) | observation, action, speech, thought, reaction, reflection, emote, location, … | every existing writer |
| Memory kind | `category` (new) | `episodic`, `semantic`, `procedural`, `social`, `belief` | derived at write time, overridable |

Default mapping (applied in `Player.add_memory` when no explicit category is
passed; unknown types degrade to `episodic`):

- `episodic` — things that happened: observation, action, speech, thought, reaction, emote, location, discovery, conversation, combat, failure, success.
- `semantic` — generalized knowledge: reflections that state a generalization ("the cellar is always locked"), consolidation summaries.
- `procedural` — how-to / expectation-of-behaviour ("when the bell rings, hide"). Authored via effects or the editor; rarely runtime-written.
- `social` — any memory carrying a `rel:<name>` tag (the task-350 convention); automatically categorized, so `derive.py` profiles and this category agree by construction.
- `belief` — a conclusion the character holds that may be wrong: first-order reflections, consolidation beliefs, contradiction resolutions.

`backstory`/seed memories (`source: manual`, negative ticks) keep their type and
are `episodic` unless authored otherwise; the SEED badge already distinguishes
them in the UI.

**The prompt consequence**: retrieval stops returning "10 random-ish events"
and returns a structured character model (§7):

```text
EVENTS          episodic memories matched to the situation
BELIEFS         what the character has concluded (with confidence)
SOCIAL MODEL    rel-tagged beliefs and feelings per person
EXPECTATIONS    procedural/behavioural conclusions
```

---

## 2. Dynamic fields

Every memory gains optional dynamics fields. All are **additive and optional** —
serialization round-trips the list verbatim (`engine/serialization.py` writes
and reloads it untouched), every reader already uses `.get()` with defaults, and
old saves without the fields load exactly as before. `engine/memory_dynamics.py`
owns the arithmetic; nothing else mutates these fields.

```json
{
  "category": "episodic",
  "activation": 0.82,          // 0..1 — how available this memory is right now
  "confidence": 0.91,          // 0..1 — how sure the character is it happened / is true
  "reinforcements": 4,         // times re-encountered or re-recalled
  "last_recalled_tick": 1823,
  "reflection_depth": 0,       // 0 = raw experience; 1 = derived from experience; never higher
  "source_memory_ids": [],     // the memories a derived memory was built from
  "contradicts": []            // ids of memories this one conflicts with (symmetric)
}
```

Defaults when absent (applied lazily by `ensure_dynamics()` — a save from any
era behaves correctly): `activation` 1.0, `confidence` 1.0 for
`manual`/`preconceived` sources and 0.7 for runtime sources, `reinforcements`
0, `reflection_depth` 0, empty id lists.

`importance` (1–10) stays exactly what it is today: the **authored base
weight** captured at encoding. It does not get rewritten by recall (the current
`Player.get_relevant_memories` "+1 on recall" bump is replaced by the
reinforcement system, which is idempotent and bounded instead of a one-way
ratchet to 10). What changes over time is computed:

```text
effective_importance(m) = importance
                        × (0.6 + 0.4 × activation)      # faded = less pressing
                        × (0.75 + 0.25 × confidence)    # doubted = less weight
```

Effective importance is **derived, never persisted** — it is a function call in
the scorers, not a stored field (runtime-derived values do not become stored
state).

### 2a. Reinforcement

Two triggers, one function (`memory_dynamics.reinforce(memory, tick, …)`):

1. **Recall reinforces.** Every retrieval path — `Player.get_relevant_memories`,
   `AgentMind.recall`, the `/memories/retrieve` endpoint, the vector-search
   merge in `memory-context.js` — stamps `reinforcements += 1`,
   `activation = min(1, activation + 0.15)`, `last_recalled_tick = tick`, and
   drifts confidence up by `+0.02` (cap 1.0). Thinking about your father's
   death keeps it accessible; that is the natural feedback loop.
2. **Re-encounter reinforces instead of duplicating.** The write-time dedup in
   `routes/memories.py` (`_is_near_duplicate`, Jaccard ≥ 0.8) currently only
   collapses same-tick triple-writes. It is extended: a near-verbatim
   re-encounter at any tick distance (same subject entity, Jaccard ≥ 0.75)
   **reinforces the original memory** and appends nothing. "Anna lied to me"
   written three times across three days becomes one memory with
   `reinforcements: 3` and rising confidence — plus, through reflection (§4),
   the semantic "Anna has repeatedly lied to me". `force: true` (editor,
   generator saves) still appends unconditionally.

Reinforcement is the anti-cap pile-up mechanism too: when a retention cap
(`memory.max_per_character`) trims, rank candidates by
effective_importance + reinforcements so repeated experience survives and
one-off noise goes first (manual/backstory memories stay protected exactly as
`_trim_memories` does today).

### 2b. Non-uniform decay

Decay exists today but is a flat trait-gated salience subtraction
(`AgentMind.apply_decay`, inert without a `memory_decay_per_tick` trait). It is
reworked to decay **activation**, with per-memory resistance, in one place
(`memory_dynamics.apply_decay`), keeping the existing gates:

- Still gated by the trait effect **and** a new `memory.decay_per_tick`
  runtime-config default (small, e.g. 0.01/tick) so ordinary characters finally
  decay something while scenarios can set the key to 0 to freeze memory.
  Trait rates *multiply* the configured rate, preserving the trait system's
  meaning (a trait that slows decay still slows it).
- `preconceived` never decays (unchanged); `background` at half rate (unchanged).
- Resistance factors multiply the step down:
  - base importance ≥ 8 → ×0.4; ≥ 6 → ×0.7 (the father's-death clause)
  - any attached emotion with intensity ≥ 7 → ×0.6 (emotionally encoded
    memories persist — `memory_emotions` is already the rich form)
  - `1 − 0.1 × min(reinforcements, 6)` (repeated experience fades slowest)
  - category `semantic`/`belief`/`procedural` → ×0.3 (conclusions outlive events)
- Removal: when `activation` decays to ≤ 0.01 **and** the memory is not
  important (base < 6, no reinforcement, `manual`/`preconceived` never), it is
  removed and the observation index forgets it (re-enchanting the world,
  task-425 semantics preserved). Important memories never delete; they just
  become less available until recalled again.

Decay therefore produces the intended ladder: breakfast fades in hours, a
threatened-knife memory persists, an identity-defining seed memory is
effectively permanent.

---

## 3. Contradiction — fallible characters

Characters must be allowed to remember wrong things. Two detection paths, both
**marking** rather than resolving (the character, not the engine, resolves):

1. **Structural, at write time** (`memory_dynamics.detect_contradiction`,
   on both the engine and HTTP write paths): when a new memory shares an
   entity with an existing one, and the pair shows **negation asymmetry** (one
   asserts what the other denies — negation markers
   `never/not/didn't/denied/isn't/no longer` on one side, absent on the other,
   with ≥ 2 shared content words or Jaccard ≥ 0.4), the ids are linked
   symmetrically in `contradicts` and the older memory's confidence drops
   ×0.9. **Attitude statements are exempt** — a first-person feeling ("I do
   not trust Anna…") is not a factual denial; conflicting feelings belong to
   the derive.py sentiment dimensions (this false-positive class was caught
   live and excluded). The editor's link list syncs both sides on save.
2. **Interpretive, via reflection**: the reflection prompt (§4) receives any
   contradicting pairs among its source memories and may emit a resolution
   belief ("Anna probably entered the cellar") with its own confidence —
   leaving the original episodes untouched and still linked.

A belief with an unresolved contradiction renders in the UI as
`Confidence 71% · contradicts tick 1762` and in the prompt as
`(you are not sure — this conflicts with what you remember at tick 1762)`.
No system may silently resolve a contradiction into objective truth.

---

## 4. Reflection 2.0 — reflect to change, not to summarize

Today's `reflect()` retrieves importance ≥ 6, asks for 1–2 summary sentences,
and appends them as importance-8 `reflection` memories. Two problems: the
insight changes nothing, and reflections feed later reflections (summaries of
summaries).

**Structured reflection.** The client prompt (static/js/agent/memory-manager.ts)
asks for actionable JSON instead:

```json
{"insights": [{
   "belief": "Anna is probably lying about the cellar.",
   "about": ["Anna"],
   "confidence": 0.7,
   "emotional": {"label": "suspicion", "intensity": 6},
   "behavior": "Verify Anna's claims independently before acting on them.",
   "relationship": {"who": "Anna", "dim": "trust", "delta": -2}
}]}
```

The backend `/memories/reflect` accepts **both** the old string-list payload
(existing callers, MCP, tests keep working) and the structured one, and stores
each insight as a `belief`-category memory stamped with `reflection_depth: 1`,
`source_memory_ids` (the ids reflected on), `confidence`, resolved
`entity_ids` (via `engine/matching.py` — names to ids, never names as keys),
`rel:<name>` tags for relationship insights (which is all `derive.py` needs to
fold the delta into the per-person profile — no second writer), and the
`behavior` insight stored as a `procedural` memory linked to the same sources.
The emotional association re-feels through the existing
`/emotions/map` respike path.

**The recursion guard, enforced twice.** The client excludes
`reflection_depth ≥ 1` memories from its reflect inputs; the backend rejects
insights whose `source_memory_ids` all carry `reflection_depth ≥ 1` unless
`force: true`. The derivation ladder is therefore fixed:

```text
episodic  →  reflection depth 1 (belief / semantic / procedural)   ⟠ STOP
```

**Consolidation.** The hygiene half of "50 episodes → 8 episodes → 3 beliefs"
is deterministic and server-side (`memory_dynamics.consolidate`, called from
the same tick hook as decay, config-gated): when a memory cap or a soft
threshold pressures the store, old low-importance episodic memories sharing an
entity are compressed into one `semantic` trace memory
("Between ticks 120 and 480 you had eight minor exchanges with the shopkeeper.")
whose `source_memory_ids` records exactly what was folded — the episodes'
content survives as provenance, the store stays bounded, and the LLM's
reflect() handles the belief half. Runs only when a cap is configured or
`memory.consolidate` is enabled; defaults do not rewrite anyone's save.

---

## 5. Query-driven retrieval

Retrieval today is three independent pipelines (backend keyword+recency,
client keyword, vector search) merged client-side. The scoring is upgraded in
one place — the backend `/memories/retrieve` — and the client asks it better
questions:

- **Query built from the situation** (already partially true: area + last
  thought + heard lines; extended with the current interlocutor and any active
  `rel:` context, so "Anna is approaching while hiding something" retrieves
  Anna's threat history, not just room keywords).
- **One scorer, many signals**: keyword overlap, entity-graph match (memory
  `entity_ids` vs entities named in the query — relationship history beats
  vector noise), recency (exponential, half-life ≈ 300 ticks, replacing the
  current linear `1 − tick/500` that goes negative past tick 500),
  effective_importance (§2), emotion match (an emotion label in the query
  boosts memories encoded with that emotion), and suppressed/superseded
  filtering (the current endpoint forgets both; `get_relevant_memories`
  remembers — they now agree).
- **The character model is guaranteed seat time**: when any `belief`/`semantic`
  memory matches the query's entities, the response's top slots reserve room
  for it even when episodic matches outscore it — the LLM should not get pure
  event soup when a conclusion exists.
- **Structured response** (`structured: true`): the same memories, grouped as
  `events` / `beliefs` / `social` / `expectations`, so the client prompt block
  reads as the four-section character model instead of a flat list. The vector
  merge and the dedup keep working exactly as now — the grouping is a view, not
  a second store.

---

## 6. Emergent character state (what memory does to the character)

The system already derives per-person profiles from tagged memories —
`engine/derive.py` folds `rel:<name>` memories with `dim:delta` tags into
trust / fear / attraction / disgust / respect per person, weighted by
importance and salience. That **is** the "Trust in Anna: 18/100, Fear: 74/100"
layer, and it is emergent from remembered experience, not authored stats.

The dynamics layer feeds it and the UI surfaces it:

- Reflection relationship deltas write `rel:`-tagged belief memories (§4), so
  conclusions move the profile through the existing reducer — one writer, no
  duplicated state.
- The memory UI renders the derived profile per person (the mockup's
  "Relationship: Anna" panel), and the inspector's memory detail shows which
  memories contributed.
- No new persisted personality store. If a number about a person exists
  anywhere, it is computed from memories + the relationship seed by
  `derive.py`.

---

## 7. The interface (mockup: `docs/design/memory-mockup.html`)

The character inspector's Memories tab grows from a flat list into the memory
mind, in stages:

1. **Stats header** — count by category, average confidence, total
   reinforcements, decay pressure (how much is currently below 0.5
   activation).
2. **Category filters** — All / Episodic / Beliefs / Social / Reflections
   alongside the existing text search.
3. **Dynamics on every card** — category chip, confidence %, `×N` reinforced
   badge, `⚡ contradicts` link count, faded styling for low activation.
4. **Connections** — the memory detail lists what it contradicts, what it was
   derived from, and sibling memories sharing its entities (the relationship
   history view).
5. **Per-person panel** — the derived trust/fear/… profile from `derive.py`.
6. **The full dashboard** (timeline ribbon, memory graph, decay chart) —
   designed in the mockup, filed as its own task; stages 1–5 land inside the
   existing inspector first.

The editor gains Category and Confidence controls; everything else it already
does (types, emotions, entity references, negative-tick seeds, embedding
status) is kept.

---

## 8. Compatibility contract

The rule for every change: **additive fields, old callers untouched, one
writer per field.**

| Consumer | Why it is safe |
|---|---|
| `serialization.py` round-trip | Memories are stored/reloaded verbatim; new fields ride along, old saves lack them and default lazily |
| `routes/memories.py` CRUD + `PUT` replace | Editor writes whole entries; new fields optional in payloads |
| Trigger effects (`grant_memory`, `surface_memory`, `suppress_memory`) | Operate on text/tags/salience_override; untouched |
| `AgentMind` (need-driven recall, preconceived knowledge) | Gains reinforcement stamps; matching logic unchanged |
| Tick decay hook (`tick_manager`) | Same call site, new module behind it; trait gating preserved |
| HTC / agent prompts | `buildMemoryContext` keeps its shape; the I REMEMBER block gains subsections (a prompt-format change the LLM adapts to, endpoints unchanged) |
| Soak / MCP memory tools | Write plain memories; dynamics defaults apply |
| Observation memory (`record_observation`, `memory_index`) | Live per-subject beliefs keep their refresh-in-place semantics; dynamics fields coexist (`visits` already foreshadows reinforcement) |
| `derive.py` profiles | Reads tags/importance/salience — unchanged; gets better-fed by reflection deltas |

Risks called out honestly:

- **Recall-reinforcement mutates on read.** Retrieval endpoints become
  writers. Mitigation: only the tick/activation fields change, all monotonic
  and bounded; `preview` mode (Agent Lens) never reinforces, exactly as it
  never respikes today.
- **Default-on decay changes existing scenarios.** The default rate is small,
  important/emotional/reinforced/semantic memories are resistant, and
  `memory.decay_per_tick: 0` freezes it. Filing as a deliberate behaviour
  change, not a silent one.
- **Structural contradiction detection can false-positive.** It only links;
  it never deletes, never rewrites text, and lowers confidence by ≤ 10%. A
  wrong link is visible and removable in the editor.

---

## 9. What this is not

- Not a second memory store. Everything lands on `Player.memories[]`.
- Not an ontology or world-model rebuild — `AgentMind`'s seam stays the seam.
- Not LLM-at-tick: all tick-driven dynamics (decay, reinforcement, consolidation)
  are deterministic arithmetic; the LLM is invoked exactly where it already is
  (react memory, reflect) with better contracts.
- Not a replacement for `SpatialMemory` / `visited_areas` / `discovered_items`
  (discovery state) or `VectorStore` (the index) — §5 composes with them.

## 10. Related

- [[Memory System]] — the existing one-store architecture (unchanged by this)
- [[Characters/Emotion & Affect System]] — affect dimensions the respike writes
- [[dev_tasks/done/characters/task-178-unify-memory-systems|task-178: unify memory systems]]
- [[dev_tasks/done/characters/task-346-memory-write-dedup-same-tick-type-varied|task-346: write-time dedup]]
- Mockup: `docs/design/memory-mockup.html` (static, not wired)

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Read next** — [[Memory System#Memory dynamics (task-685)]], [[Agent Engine#Memory in the agent]], [[Agent Engine#Structured Actions (task-160)]], [[Emotion & Affect System#How memory emotions reach the character]]

**Neighbouring notes** — [[Agent Engine]], [[LLM Providers]], [[Memory System]], [[Narration System]], [[Turn-Based System]]

<!-- connected:end -->
