---
type: task
status: todo
area: characters
priority: medium
---

# task-447: Character nicknames / aliases (authoring + resolution)

**Filed:** 2026-09-22
**Related:** task-446 (id-first node identity), task-448 (ambiguous target prompt),
`engine/matching.py` (character alias tier), `engine/serialization.py`

## Why

A character can go by a short name the game must resolve: "Vi" for *Violet
Halloway*. Nicknames are a **resolution-layer** concern — they map spoken input
to an identity; the data stays id-keyed. The engine already has a character
**alias tier** (`matching.py` `_match_character_name` step 2b, reading the node's
`aliases` property via `node_aliases`), but there is no way to author it and it
does not persist.

Note: "Vi" is *not* a substring of "Violet" (matching is word-boundary aware), so
a nickname cannot be inferred — it must be declared.

## Problem

1. **No authoring surface.** Character nodes in scenarios carry only
   `personality`; the inspector/library has no nicknames field.
2. **Aliases do not survive save/load.** On load a character's graph node is
   recreated bare — `Node(id, type="character", name=pname)` with no properties
   (`serialization.py`) — so an authored alias on the node would be lost. The
   alias must live where player state round-trips (the player payload) or be
   re-applied on load.

## Scope

- Add a **nicknames/aliases** field for characters in the inspector and library
  editor (list, or comma/`|`-separated like other alias fields).
- Persist it: store on the player payload (or a node-properties map that
  serialization restores) so it survives save/load and library import/export.
- Resolve it: the existing character alias tier already returns **candidates**
  when several characters share an alias — keep that (it feeds task-448).
- Consider surfacing aliases in autocomplete and in the target prompt.

## Acceptance

- Author can add "Vi" to Violet Halloway; `look`, `approach`, `talk to vi`
  resolve to that character.
- Alias survives a save → load and a library round-trip.
- Two characters sharing an alias return an ambiguous candidate set (not a silent
  pick).

## Non-goals

- Duplicate **display** names (task-446).
- The disambiguation prompt UX (task-448).
