---
type: task
status: todo
area: world
priority: medium
---

# task-529: Feature-entry direction phrases (narrative move verbs on entry edges)

**Filed:** 2026-09-26
**Related:** task-496 task-525

## Goal

Replace the hardcoded in/out gateway directions with a phrase the feature/placement owns: enter, enter the mine, climb up the rockface, descend the shaft. Exterior cell-to-cell moves stay compass north/south/east/west (+ diagonals); only the exterior->feature seam gets narrative verbs. The engine already resolves movement by the direction string, so no engine change is required - the compiler/gateway must carry the phrase and the area description must offer it ('a cave mouth yawns here; you could enter'). Decide where the phrase is sourced (feature/biome record, placement field, or scope record), how it is validated/deterministically defaulted, and how the walker and prompt list it as an available move.

## Acceptance

- TODO
