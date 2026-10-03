---
type: task
status: todo
area: gameplay
priority: medium
---

# task-683: WITNESSED speech line attributes a line to a door instead of to the person who spoke it

**Filed:** 2026-10-04
**Related:** 

## Goal

As Jake in the foyer the panel shows: [Heard from the library_door_back -> to you] a woman's voice said: elena!! the bookcase ... The direction is a door node, not a speaker, so the line reads as if the door talked. A character standing in earshot should be attributed the way any other agent would perceive it. Reporter has not yet pinned the expectation (speaker named vs anonymous voice with a correct origin), so confirm the intended rendering before implementing, and trace which layer supplies the Heard from value (sound propagation vs the prompt builder) rather than patching the rendered string.

## Acceptance

- TODO
