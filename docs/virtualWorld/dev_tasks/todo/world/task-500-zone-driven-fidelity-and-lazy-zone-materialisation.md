---
type: task
status: todo
area: world
priority: medium
---

# task-500: Zone-driven fidelity and lazy zone materialisation

**Filed:** 2026-09-24
**Related:** task-399, task-495, task-401, task-411, task-418
**Design:** `docs/design/worldpainter-knowledge-and-fog.md`

**Overlaps task-401 and task-411.** task-401 already owns chunk load/evict (the actual materialisation), and task-411 (selector) + task-418 (awareness channels) own fidelity-tier selection. This task's only unique delta is using *zones* as the selection key and keeping WorldPainter-side zone records — consider folding it into 401/411 rather than tracking it separately.

## Goal

Use zones (world_scopes) as the spatial key for the existing fidelity tiers (task-399 background fidelity; engine/soak.py promote/demote; engine/trace.py records promote/demote). Distant zones should exist as scope records only and materialise their areas/ways on approach (lazy instantiation), so a 500-zone world does not hold every area/way node at once - this is the actual offloading win. Tie to task-411/412/418 attention tiers and task-407 graph edge-indexing/perf.

## Acceptance

- Fidelity-tier selection can key off a character's zone/scope (in addition to attention).
- Distant zones hold only scope records; their areas/ways are materialised on approach and can be released — a test proves node count stays bounded as the world grows.
- Promotion/demotion records survive materialise/release (`engine/trace.py`).
