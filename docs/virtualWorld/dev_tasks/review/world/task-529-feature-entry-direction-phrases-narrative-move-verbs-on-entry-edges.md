---
type: task
status: review
area: world
priority: medium
---

# task-529: Feature-entry direction phrases (narrative move verbs on entry edges)

**Filed:** 2026-09-26
**Related:** task-496 task-525

## Goal

Replace the hardcoded in/out gateway directions with a phrase the feature/placement owns: enter, enter the mine, climb up the rockface, descend the shaft. Exterior cell-to-cell moves stay compass north/south/east/west (+ diagonals); only the exterior->feature seam gets narrative verbs. The engine already resolves movement by the direction string, so no engine change is required - the compiler/gateway must carry the phrase and the area description must offer it ('a cave mouth yawns here; you could enter'). Decide where the phrase is sourced (feature/biome record, placement field, or scope record), how it is validated/deterministically defaulted, and how the walker and prompt list it as an available move.

## Acceptance

## Acceptance

- [x] **The phrase is owned by the record.** `tunnel`, `gate`, `bridge`, `ford`
      and `ruin` declare `entry_phrase` / `exit_phrase` / `entry_aliases` in
      `data/worldpainter/biomes.json`, and `biomes_mod.entry_phrases()` reads
      them. A tunnel says "go down the tunnel", not the derived "enter the
      shaft" — a modder edits one JSON field and the world changes.
- [x] **The placement outranks the record**, as `placements[child].entry_phrase`:
      a mine with two adits has two ways in and only the author knows which is
      which. A placement phrase is honoured verbatim and still keeps the record's
      short `in`/`out` handles.
- [x] **The derived phrase is the last resort**, and only when neither source
      speaks — which is the point: the chain has an order, and the order is in one
      function.
- [x] **The author's phrase survives a Generate.** Placement records are rebuilt
      from the cell on every compile, so author-owned keys are carried through
      and only the compiler's own keys (`_DERIVED_PLACEMENT_KEYS`) are
      overwritten. Checked by compiling twice: the phrase is still there.
- [x] **The description offers the move**: a seam with an `entry_phrase` reads
      "You could go down the tunnel — Shaft is on the other side." rather than
      `[go down the tunnel] is clear`. A shut one reads "You could enter the
      tavern, but the tavern's door is shut and the sign is turned."
- [x] **Exterior cell-to-cell moves are untouched** — still `north`/`south`/
      `east`/`west` and the diagonals. Only the exterior→feature seam is narrative.
- [x] A building's `in` way carries its phrase too, so a town street offers its
      doorways the same way a cliff offers its tunnel.

## Notes

- The phrase is recorded on the way as `entry_phrase` **and** kept as the
  `direction`, because movement already resolves by the direction string: the
  engine needs no change, which was the task's expectation.
- The "cave mouth yawns here" prose was deliberately not added as a *biome
  description*. The offer line already puts the mouth in the room the character
  is standing in, which is where the author can see it, rather than in the
  inventory of the thing behind it.
