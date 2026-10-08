---
type: task
status: todo
area: ui
priority: medium
---

# task-730: Chat-based interactive memory creation: the character reacts in voice to author new memories

**Filed:** 2026-10-07
**Related:** task-42, task-691, task-714, task-729, task-404

## Goal

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

- [ ] The character's reply reflects its authored personality and its existing
      memory / relationship state. Measured, not assumed: the same prompt against
      two characters with different personalities and memory sets yields
      character-appropriate, different replies.
- [ ] The reply is consistent with existing memories — it must not fabricate a
      blatant contradiction the engine's contradiction detector (task-689) would
      flag. Where it links to prior memories, it uses the existing entity
      references / same-entity connections, not a parallel index.
- [ ] The designer can iterate: at least one follow-up turn that visibly changes
      the draft, and an explicit accept.
- [ ] Accepting writes exactly one memory via the existing `addPlayerMemory` path,
      with tags and `memory_emotions`; no new persistence. Cancelling writes
      nothing.
- [ ] With no LLM configured the flow reports an honest error rather than a silent
      no-op (bug-514's lesson).
- [ ] `npm run build:ts` and `node tools/unit/run.cjs` pass.

## Open questions

- Does the character speak as itself ("I remember when…") or does the surface
  summarise what it *would* feel? The request implies first-person recall.
- Reuse `_identityBlock` / `_buildSeedPrompt`, or a new prompt that pulls recalled
  memories through the existing recall system (`engine/` recall + the
  prompt-builder memory-context module)?
- Where the transcript lives — the generation modal, or a panel of the Mind
  surface (task-729).
- Whether the saved memory gets a distinct `source` (e.g. `manual:authored`) so an
  authored memory is distinguishable from a lived one. bug-519 shows editorial
  residue must be identifiable.
