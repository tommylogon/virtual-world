---
type: task
status: todo
area: characters
priority: high
---

# task-457: Character nodes are the canonical character record (human, agent, simple NPC)

**Filed:** 2026-09-22
**Related:** task-446, task-316

## Goal

Make the character graph node the single source of truth for a character's full definition (stats, skills, vitals, traits, tags, interest_tags, personality, descriptions, emotion, conditions, simple_npc/autonomy/behaviour fields; inventory/equipped via edges). The Player object becomes a runtime view derived from and synced with the node: load seeds node properties from the players section (additive migration), node writes are authoritative, and no defining field lives only on the Player. Uniform for human, agent, soak and simple NPCs.

## Acceptance

- TODO
