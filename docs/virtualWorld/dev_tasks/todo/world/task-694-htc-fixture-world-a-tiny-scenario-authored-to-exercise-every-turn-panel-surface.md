---
type: task
status: todo
area: world
priority: high
---

# task-694: HTC fixture world: a tiny scenario authored to exercise every turn-panel surface

**Filed:** 2026-10-04
**Related:** task-677,task-448,bug-23,bug-521,task-679

## Goal

TODO

## Acceptance
A small world (10-20 areas) authored ONCE so the harness (task-693) can exercise
everything the human turn panel does. Content before instrumentation — the fixture
is what makes the checks real.

- [ ] Painted `cell` + `world_scope_id` on every area, so the minimap lattice draws
      (mansion cannot — see task-677's UNMET note).
- [ ] TWO characters sharing a display name in one area, and two sharing a
      nickname across areas — exercises the engine's `__suffix` uniquing, the
      duplicate-import path (bug-521) and task-448's chooser.
- [ ] One hidden way behind a false wall, one locked door, one blocked way —
      exercises bug-23's negative and the way-knowledge gate.
- [ ] One scripted simple NPC with the zombie's behavior shapes (message, damage on
      enter, go-toward-noise) and one human-controlled character with
      preconceived knowledge.
- [ ] At least one item with a flavor trigger and one grapple-ready prop.
- [ ] The harness boots into it and the turn panel opens on the human's slot
      without authoring errors (`tools/tasks.py validate`-equivalent: scenario
      integrity checks green).

