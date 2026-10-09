---
type: task
status: review
area: ui
priority: high
---

# task-752: NL editor overlay ships all 627 areas every call; scope the world summary to the selection and counts

**Filed:** 2026-10-09
**Related:** task-422 (NL editor budget controls), task-739 (read tools)

## Goal

Every NL editor turn ships the **entire** world summary in the system prompt: all
areas (627 in kraktooth_goblin_camp) and the full character roster, regardless of
what the user asked. Measured from a captured exchange:

- `input_tokens: 32,833` for the question *"what behaviours does the zombies
  have?"* (answer: ~34 tokens output).
- The 627 `- Area [name] (id: …) [tags: …]` lines are roughly **15–16k tokens**;
  the 27-line roster ~500; ~30 tool definitions make up most of the rest.

The bulk is contextually irrelevant: a question about zombies pulls in every road
tile across West woods / deep woods / Eldenford interior / world.

Cause: `static/js/nl-editor/tools.ts:221-258` — `listWorldSummary()` iterates every
graph node and pushes **every** area into `areas[]` with no cap, no scope filter
and no relevance filter, then `agent-loop.buildSystemPrompt()`
(`agent-loop.ts:294-295`) embeds the result verbatim on every call.

This is also a likely contributor to the model stalling after narrating a plan
(see the "dots-3 preview" exchange): 600+ irrelevant lines bury the selection and
lose the thread before the model acts.

The read tools already exist to fetch specifics on demand — `list_nodes`
(filter/paged), `search_graph_nodes` (fuzzy), `get_node`, `list_world_summary` —
so the overlay does not need to be the whole world.

## Plan

1. Overlay carries **counts** plus only the selection's neighbourhood: the
   selected node's area and its directly connected areas (or the active scope's
   areas), capped (~30). The rest is discoverable via `search_graph_nodes` /
   `list_nodes`.
2. Roster the same way: full roster only when small; otherwise a count plus the
   characters in the selection's area.
3. Record the before/after input-token count in the card.

## Acceptance

- [ ] A representative world's overlay no longer lists hundreds of areas; counts
      replace the long tail.
- [ ] The selected node's area and immediate neighbours still appear (selection
      awareness preserved — rule 3).
- [ ] The model can still answer "who is in area X" / "how many goblins" by
      calling `list_nodes`; those tools are unchanged.
- [ ] Measured input tokens for the same question dropped materially (before:
      ~32,800), recorded here.
- [ ] No regression in the read tools or in prompt rules 1–15.

## Implementation (2026-10-09)

- `nl-editor/tools.ts` — `listWorldSummary()` now emits counts plus a bounded
  (≤30) selection-first area slice and a truncation note; `roster()` capped at 40
  with a note. New `_selectedAreaIds()` resolves the selection's area (via `in`/`at`
  edge) and its neighbours through `connection` edges (area→way→area).
- Bundled with: `agent-loop.ts` prompt rule 16 (act, don't narrate);
  `tool_calls: []` normalised to absent in `agent-loop.ts` and `llm-client.ts`;
  NL editor `A−/A+` chat font size (`ui.ts`, persisted `vw_nl_fontSize`).
- Gates: `build:ts`, `typecheck`, `js unit` all clean (632 pass).
- **Not yet verified live:** the before/after input-token count on the same
  question (needs a browser call to re-measure; ~627→≤30 area lines should remove
  roughly 15k of the ~32.8k input tokens).
