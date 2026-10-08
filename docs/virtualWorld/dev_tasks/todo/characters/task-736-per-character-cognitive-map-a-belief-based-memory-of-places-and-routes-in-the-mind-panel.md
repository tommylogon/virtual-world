---
type: task
status: todo
area: characters
priority: medium
---

# task-736: Per-character cognitive map: a belief-based memory of places and routes in the Mind panel

**Filed:** 2026-10-08
**Related:** task-714, task-734, task-691, task-677, task-581

## Goal

Give each character a mental map of the places they remember and the ways they know to reach them: a belief-based (not truth-based) projection of that character's place and route memory, rendered per character and shown in the Mind panel. It may be incomplete or wrong - the character believes the door is open, or that the mill is east. Reuse the existing spatial-memory data (known_way_aspects, discovered_exits, visited_areas) and the turn-minimap rendering; do not add a new store.

## Grounding (measured 2026-10-07)

The spatial memory already exists and is written; it just has no view:

- `engine/agent_memory.py` — `known_way_aspects`, a bucket per `(way_id, aspect)`.
- `engine/movement.py` — writes spatial memory on a crossing ("spatial memory's
  known-route").
- `discovered_exits` — the `(area, direction)` pairs the character has seen;
  read by `narration.py` (unexplored exits) and `room-context.ts`.
- `visited_areas` — areas entered.
- `static/js/agent/turn-minimap.ts` — the existing "where you've been" renderer
  (task-677), currently for the human turn panel.

## Design

A **cognitive map** is the character's *beliefs* about geography, not the world's
truth:

- **Belief-based, not truth-based.** It shows remembered areas and known ways.
  It may be **incomplete** (an area never visited) or **wrong** (the character
  believes a door is passable, or that the mill is east). This is the difference
  from the human fog-of-war minimap (truth of exploration) and the world graph
  (ground truth).
- **Derived, not stored.** It is a projection of `known_way_aspects` /
  `discovered_exits` / `visited_areas` (task-734: derived indexes stay derived).
  No new per-character store.
- **Routes = "how to get there".** Pick two remembered places and show the
  route if the character knows one — a path within the known subgraph, using only
  edges the character has traversed or been told about. A known place with no
  known route renders as disconnected.
- **The agent asks with `recall`** (free, task-352). The retrieval verb is `recall`
  — by name ("the hospital"), by intent ("somewhere a healer works"), or by tag — and
  it returns the known place and route, or an **honest negative** so the agent does
  not hallucinate. `remember` is reserved for the passive `=== I REMEMBER ===` prompt
  block; the deliberate action is `recall`. Do not use `remember` as the verb.
- **Host and rendering.** Reuse `turn-minimap.ts`'s rendering; mount it in the
  Mind panel (task-714/691) as the "world knowledge (known-locations map)" the
  Mind panel already lists. The Mind panel is per character, so the map is too.

## Relationship to task-734

If knowledge is a memory record (734), then "a place I remember" and "a way I
know" are semantic/procedural records, and this map is their **visualization**.
The map and the memory model are one dataset in two views — not a second store.
`known_way_aspects` is the memory; the map is the projection.

## Open questions

- Does the map include places known only by **hearsay** (someone told you), with
  no visit? That needs a "told about" source on the record (734's `source`).
- `known_way_aspects` carries aspects (states, hazards); does the map show edge
  *attributes* ("there is a locked gate here"), or only existence?
- **Stale beliefs** have no mechanic yet — a character cannot currently hold a
  belief that is false against the graph. Decide whether the map may show a
  remembered-but-now-wrong edge, or whether it must reconcile on next perception.
- Scale: a large world visited over years is a big known subgraph; render a
  neighbourhood or the whole known set?

## Acceptance

- [ ] The Mind panel shows, for one character, the areas and ways *that
      character* knows — not the world's full graph.
- [ ] An area never visited by that character does not appear.
- [ ] A route between two known places renders if the character knows one.
- [ ] No new persisted store: it reads `known_way_aspects` / `discovered_exits` /
      `visited_areas`.
- [ ] `npm run build:ts` and `node tools/unit/run.cjs` pass.
- [ ] Live: walk a character through several areas, open the Mind panel, and see
      its map grow; confirm it differs from a second character's.
