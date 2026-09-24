---
type: task
status: todo
area: world
priority: medium
---

# task-499: Per-agent fog of war and map knowledge transfer

**Filed:** 2026-09-24
**Related:** task-495, task-403
**Design:** `docs/design/worldpainter-knowledge-and-fog.md` — fog is the
knowledge dimension of the painted grid (movement + reveal + belief travel,
task-467).

## Goal

Add an area/scope-level known set per character. player.known already gates hidden ways and items through viewer-aware perception (engine/room_perception.py; tests/test_known.py), and EDGE_KNOWN is abilities-only. Unknown cells/zones are fog on the map; walking, examining, or finding a map item reveals them - a map's use/read teaches known entries (reuse the existing teach path). Rendering: the map view shows only known cells/zones. Keep perception honest in agent prompts (an unaware agent is not told about unknown areas).

## Acceptance

- Areas/scopes can be marked known per character; unknown ones are fog on the map.
- Walking and examining reveal them; a map item's use/read teaches `known` entries via the existing teach path.
- Agent prompts never disclose unknown areas (perception stays honest).
- Tests cover the reveal, the fog-rendering data, and map-item knowledge transfer.
