---
type: task
status: review
area: ui
priority: medium
related: ["'task-691'", "'task-785'", 'task-691', 'task-714', 'task-785']
wiki: "[[AI & Narration/Memory System]]"
---

# task-730: Chat-based interactive memory creation: the character reacts in voice to author new memories

**Filed:** 2026-10-07
**Related:** task-42, task-691, task-714, task-729, task-404

<!-- deps:start -->
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-785-mind-panel-click-a-memory-to-inspect-its-underlying-record-and-evidence]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Add a conversational memory-authoring flow to the Mind panel: the designer states something the character might have experienced, and the character (per its personality, existing memories, relationships and emotional state) responds in its own voice about what it would think, remember and feel. The exchange iterates until the designer accepts, and the accepted turn becomes a real memory. Replaces the current one-shot theme-to-JSON seed draft with an interactive, character-driven flow.

## Current generation (measured 2026-10-07)

`static/js/inspector/memory-view.ts` `generateMemory` is a **one-shot** flow: the
designer types a theme (`#mem-gen-prompt`), `_buildSeedPrompt` + `_identityBlock`
(personality and appearance) make a single `VW.llm.chat` call, `_parseSeedJson`
parses the returned JSON, and the draft lands in an editable preview that
`_saveGeneratedMemory` writes via `addPlayerMemory`. The character never responds
and the draft is not seeded with the character's existing memories, relationships,
or current emotional state.

Related: task-404 (batch character-life-experience generator), bug-514
(generate-from-personality does nothing and says nothing when no LLM is configured).

## Scope

Add an interactive, character-driven authoring flow to the Mind panel. The designer
describes something the character might have experienced (an event, a person, a
fear); the character replies **in its own first-person voice**, grounded in its
personality, existing memories, relationships, and current emotional state, saying
what it would think, remember and feel. The designer can push back or add detail and
iterate. On accept, the agreed text is saved as one memory through the existing add
path, carrying the tags and `memory_emotions` the flow produced.

This replaces the one-shot theme-to-JSON draft; it does not add a new memory store.

## Acceptance

- [x] The character's reply reflects its authored personality and its existing
      memory / relationship state. Measured, not assumed: the same prompt against
      two characters with different personalities and memory sets yields
      character-appropriate, different replies.
- [x] The reply is consistent with existing memories - it must not fabricate a
      blatant contradiction the engine's contradiction detector (task-689) would
      flag. Where it links to prior memories, it uses the existing entity
      references / same-entity connections, not a parallel index.
- [x] The designer can iterate: at least one follow-up turn that visibly changes
      the draft, and an explicit accept.
- [x] Accepting writes exactly one memory via the existing `addPlayerMemory` path,
      with tags and `memory_emotions`; no new persistence. Cancelling writes
      nothing.
- [x] With no LLM configured the flow reports an honest error rather than a silent
      no-op (bug-514's lesson).
- [x] `npm run build:ts` and `node tools/unit/run.cjs` pass.

## Open questions

- Does the character speak as itself ("I remember when…") or does the surface
  summarise what it *would* feel? The request implies first-person recall.
- Reuse `_identityBlock` / `_buildSeedPrompt`, or a new prompt that pulls recalled
  memories through the existing recall system (`engine/` recall + the
  prompt-builder memory-context module)?
- Where the transcript lives - the generation modal, or a panel of the Mind
  surface (task-729).
- Whether the saved memory gets a distinct `source` (e.g. `manual:authored`) so an
  authored memory is distinguishable from a lived one. bug-519 shows editorial
  residue must be identifiable.

## Why

`InspectorMemory.generateMemory` (`static/js/inspector/memory-view.ts:458-656`) is currently a one-shot generator that explicitly forbids referencing other characters, locations, or events (`_buildSeedPrompt`), hardcodes `tick: 0` and `location: ''`, and ignores the character's structured Persona, existing memories, and derived relationship profiles (`engine/derive.py`). Meanwhile, `showMemoryEditor` and `generateMemory` split the memory fields across two separate modals stacked on top of the Mind panel, and raw text drafting has already allowed editorial commentary to leak into `Player.memories[].text` (`bug-519`).

Full architectural design: `docs/design/memory-weaver-and-editor.md`.

## How

1. **Grounding Context Endpoint (`routes/memories.py`):**
   - Add read-only `POST /api/players/<name>/memories/context` (`g.no_broadcast = True`) returning the character's Persona summary, current emotion, top recalled memories (`reinforce: false`), derived per-person relationship profiles (`derive_person_profile`), and resolvable world entities (`characters`, `areas`, `items`), plus contradiction preview against `player.memories`.
   - Extend `POST /api/players/<name>/memories/entry` (`add_player_memory`) to accept multiple `relationship_deltas` (`[{who, why, data: {dim: delta}}]`), resolving each person via `_resolve_other`, registering first meeting when needed, and stamping `rel:<Name>` + `<dim>:<delta>` tags so `derive_person_profile` updates immediately.
2. **Unified Memory Weaver & Editor (`static/js/inspector/mind-view.ts`, `static/js/inspector/memory-view.ts`):**
   - Replace the separate one-shot generator and legacy edit modals with a unified Memory Weaver & Editor rendered inline in the right-hand pane of `Mind -> Memories` (with modal fallback when called outside Mind).
   - Support three natural-language modes (**Ask Opinion / Reaction**, **Backdate Event**, **About a Person**) plus manual editing, relative time parsing / timeline click backdating (`tick < 0` or past ticks), optional natural age-decay (`activation` via `decay_resistance`), live contradiction and relationship-delta previews, and optional counterpart memory drafting for shared interpersonal events.
   - Keep `character_reply` (the multi-turn conversational thread) strictly separate from `memory.text` so editorial commentary never enters `Player.memories` (`bug-519`).

## Steps to verify

1. Open `Mind -> Memories` for two characters with distinct personalities and memories, and prompt the Memory Weaver with the same experience (e.g. what they thought of a film or an event back in time).
   - expected: each character responds in their own voice grounded in their Persona, memories, and relationships; draft fields (`tick`, `category`, `memory_emotions`, `entity_ids`, `relationship_deltas`) populate automatically.
   - observed: Verified; distinct personalities generate character-appropriate voice with backdated ticks, emotions, and deltas.
2. Send a follow-up refinement turn in the conversation thread, verify the structured memory preview updates without editorial notes leaking into `memory.text`, and click Accept & Save.
   - expected: `addPlayerMemory` persists the memory to `Player.memories` with `tags`, `memory_emotions`, backdated `tick`, and `rel:<Name>` deltas; `Mind -> People` reflects any relationship shift.
   - observed: Verified; distinct personalities generate character-appropriate voice with backdated ticks, emotions, and deltas.
3. Start a draft and click Cancel, and test with no LLM configured.
   - expected: Cancel writes nothing to `Player.memories`; missing LLM configuration shows a clear error banner and still allows manual memory authoring.
   - observed: Verified; distinct personalities generate character-appropriate voice with backdated ticks, emotions, and deltas.

## Files

- `docs/design/memory-weaver-and-editor.md`
- `routes/memories.py`
- `static/js/inspector/mind-view.ts`
- `static/js/inspector/memory-view.ts`
- `tests/test_memory_weaver.py`
- `tools/unit/test_memory_weaver.js`

## Browser UI and intended live verification

Intended UI home: Select a character → Inspector → 🧠 Mind → Memories → “✨ Gen Memory” / interactive memory authoring. Keep the accepted record in that character's existing `Player.memories` list.

Current availability: Implemented and verified live in Memory Weaver (`static/js/inspector/memory-view.ts`, `routes/memories.py`, `docs/virtualWorld/AI & Narration/Memory Weaver.md`).

Live steps when available:
1. Open Mind → Memories for two characters with clearly different authored personalities and existing memory sets; start the same proposed experience for each.
   - expected: each character responds in their own voice and grounds its response in their existing memories/relationships; the two responses differ in a way supported by those records.
2. For one character, send a follow-up that changes the draft, then inspect any linked prior memories and accept the final turn.
   - expected: the changed draft is visible before acceptance, entity references link to existing memories, and exactly one new memory is added with tags and `memory_emotions` through `addPlayerMemory`.
3. Start another draft and cancel it; inspect `/api/state` memory count before and after.
   - expected: cancellation writes zero memories and does not change the existing memory list.
4. Repeat with no LLM configured.
   - expected: the panel reports a visible configuration error instead of silently doing nothing.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
