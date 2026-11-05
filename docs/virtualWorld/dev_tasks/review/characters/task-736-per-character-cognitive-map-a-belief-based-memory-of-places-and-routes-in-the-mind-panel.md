---
type: task
status: todo
area: characters
priority: medium
related: ['task-404', 'task-725', 'task-734', 'task-786']
wiki: "[[World Building/Character Creation & Archetypes]]"
---

# task-736: Per-character cognitive map: a belief-based memory of places and routes in the Mind panel

**Filed:** 2026-10-08
**Related:** task-714, task-734, task-691, task-677, task-581

<!-- deps:start -->
**Related:** [[task-404-character-life-experience-generator]], [[task-725-memories-carry-nothing-about-death-vitals-travel-perception-or-resurrection]], [[task-734-knowledge-is-memory-fold-known-recipes-known-places-into-one-prose-data-record-with-episodic-vs-semantic-kinds]], [[task-786-recall-transparency-show-why-a-memory-was-recalled-automatic-and-action-driven]]
<!-- deps:end -->

## What

Give each character a mental map of the places they remember and the ways they know to reach them: a belief-based (not truth-based) projection of that character's place and route memory, rendered per character and shown in the Mind panel. It may be incomplete or wrong - the character believes the door is open, or that the mill is east. Reuse the existing spatial-memory data (known_way_aspects, discovered_exits, visited_areas) and the turn-minimap rendering; do not add a new store.

## Grounding (measured 2026-10-07)

The spatial memory already exists and is written; it just has no view:

- `engine/agent_memory.py` - `knows_way(way_id, aspect)`; it resolves the way's
  sides and writes `Player.learn_way_aspect(area_name, direction, aspect)`, so
  the real key is `known_way_aspects[(area, direction)]` (a bucket of aspects),
  not `(way_id, aspect)`.
- `engine/movement.py` - writes spatial memory on a crossing ("spatial memory's
  known-route").
- `discovered_exits` - the `(area, direction)` pairs the character has seen;
  read by `narration.py` (unexplored exits) and `room-context.ts`.
- `visited_areas` - areas entered.
- `static/js/agent/turn-minimap.ts` - the existing "where you've been" renderer
  (task-677), currently for the human turn panel.

## How

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
  route if the character knows one - a path within the known subgraph, using only
  edges the character has traversed or been told about. A known place with no
  known route renders as disconnected.
- **The agent asks with `recall`** (free, task-352). The retrieval verb is `recall`
  - by name ("the hospital"), by intent ("somewhere a healer works"), or by tag - and
  it returns the known place and route, or an **honest negative** so the agent does
  not hallucinate. `remember` is reserved for the passive `=== I REMEMBER ===` prompt
  block; the deliberate action is `recall`. Do not use `remember` as the verb.
- **Host and rendering.** Reuse `turn-minimap.ts`'s rendering; mount it in the
  Mind panel (task-714/691) as the "world knowledge (known-locations map)" the
  Mind panel already lists. The Mind panel is per character, so the map is too.

## Relationship to task-734

If knowledge is a memory record (734), then "a place I remember" and "a way I
know" are semantic/procedural records, and this map is their **visualization**.
The map and the memory model are one dataset in two views - not a second store.
`known_way_aspects` is the memory; the map is the projection.

## Open questions

- Does the map include places known only by **hearsay** (someone told you), with
  no visit? That needs a "told about" source on the record (734's `source`).
- `known_way_aspects` carries aspects (states, hazards); does the map show edge
  *attributes* ("there is a locked gate here"), or only existence?
- **Stale beliefs** have no mechanic yet - a character cannot currently hold a
  belief that is false against the graph. Decide whether the map may show a
  remembered-but-now-wrong edge, or whether it must reconcile on next perception.
- Scale: a large world visited over years is a big known subgraph; render a
  neighbourhood or the whole known set?

## Acceptance

- [ ] The Mind panel shows, for one character, the areas and ways *that
      character* knows - not the world's full graph.
- [ ] An area never visited by that character does not appear.
- [ ] A route between two known places renders if the character knows one.
- [ ] No new persisted store: it reads `known_way_aspects` / `discovered_exits` /
      `visited_areas`.
- [ ] `npm run build:ts` and `node tools/unit/run.cjs` pass.
- [ ] Live: walk a character through several areas, open the Mind panel, and see
      its map grow; confirm it differs from a second character's.

## Why

TODO

## Steps to verify

1. In a scratch scenario, select two characters who start in the same area.
   Record each character's `visited_areas`, `discovered_exits`, and
   `known_way_aspects` from `/api/state`, then open the first character's Mind
   panel.
   - expected: its map contains only that character's remembered areas and
     known routes; areas present only in the world graph are absent.
2. Move the first character through one connected area and way it did not know,
   then reopen Mind and compare the map with the updated character state.
   - expected: the newly visited area and learned way appear for that character
     only; the second character's map is unchanged.
3. Select two areas the first character knows and request the route using the
   character's existing `recall` interaction.
   - expected: a path is shown only when the character knows a connecting way;
     an unknown route returns an honest negative instead of a path from the
     world's full graph.
4. Compare the character record before and after opening the map.
   - expected: rendering does not add a cognitive-map field or otherwise write
     a second persisted store; the view is derived from the existing spatial
     memory fields.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: select a character → open the existing Mind panel →
**World knowledge / known-locations map**. The map belongs inside that
character's Mind view, beside the existing memory and knowledge content; it is
not a world-graph overlay or a separate character record.

Current availability: per-character spatial memory and the turn-panel minimap
renderer exist. The Mind-panel cognitive map described here is planned; this
card does not claim that it currently renders there.

Live steps when available:
1. Load a scratch scenario with two characters in the same starting area and
   at least two connected areas. Open Character A's Mind panel and inspect the
   known-locations map before either character moves.
   - expected: only areas and routes present in A's existing spatial-memory
     fields appear; an unvisited destination from the world graph is absent.
2. Move A across one way into the next area, then reopen the same Mind panel.
   - expected: the newly visited area and traversed route appear in A's map.
3. Select Character B, who did not move, and inspect the map.
   - expected: B's map does not gain A's visit or route.
4. Use `recall` for a route A has traversed and for a world route A has never
   learned; compare each answer with the map and `/api/state` spatial-memory
   fields.
   - expected: the learned route is returned; the unknown route is not
     inferred from ground-truth graph edges. Opening the map creates no new
     persisted cognitive-map field.

These steps describe the intended Mind-panel access and acceptance. The map is
planned and has not been represented as available today.

This section is not a claim that planned UI exists or works today.
