---
type: task
status: todo
area: gameplay
priority: low
---

# task-430: Retire `visited_areas` and `discovered_items`

**Filed:** 2026-09-21  
**Follows:** task-425 (novelty recovery and recreation), task-403 (observation
memories).

## Why this exists

task-425 replaced both sets as the *novelty* source — novelty now reads the
observation memory (`player.observation_tick`). But the sets were left in place
because they still have consumers, and both are still written so those consumers
keep working. Two structures describing the same thing (what a character has
experienced) is exactly the drift task-425 set out to remove, so this finishes
the job:

| consumer | what it reads | should read instead |
|---|---|---|
| `engine/spatial_memory.py` `build_known_routes(current_area, visited_areas)` | area **names** the character has been in | live `kind == "area"` observations (`observation_memory` / `memory_index`) |
| `engine/tick_manager.py:~313` `adventurous` micro-modifier | "is the current area new?" | `player.has_seen(area_id)` — but see the ordering note below |
| `engine/items/take_drop_actions.py` | bookkeeping only (novelty no longer reads it) | drop entirely |
| `routes/memories.py` `.../memories/spatial` | `player.visited_areas` → `build_known_routes` | same derivation as spatial memory |
| `static/js/agent/prompt-builder/room-context.js`, `memory-context.js`, `contextual-actions.js` | `player.discovered_items` for prompt context | `memory_index` / observation memories, or a server-rendered list |
| `engine/serialization.py` | round-trips both | drop, keeping the tolerant read |

## The one real snag

`visited_areas` is **area names**, while observation subjects are **area node
ids**, and `location` on an observation is also the area name. So "areas I have
been in" derives as either

- `{m["location"] for m in player.memories if m.get("kind") == "area" and not m.get("superseded_by")}`
  — a scan over memories, fine for the prompt path (`/api/...memories/spatial`)
  but not in the tick loop; or
- resolve each `kind == "area"` subject id to its node and take the name, via
  `memory_index` — no scan, but needs the graph.

Prefer the second where the graph is reachable.

**Ordering note on `adventurous`:** today `visited_areas.add()` happens *before*
the `adventurous` check, so the bonus is for the first-ever entry only, and
`observe_area` has already stamped the observation by then, so `has_seen` is
`True` on that first entry — a naive swap inverts the behaviour. Either read the
freshness `observe_area` returns (it is pre-refresh and already available in
`movement.py`) or accept the change deliberately.

## Acceptance

- `grep -rn "visited_areas\|discovered_items"` returns only the tolerant
  legacy read in `engine/serialization.py`.
- An old save carrying both sets loads without error and its known-route block
  is non-empty for areas the character has actually been in.
- The `adventurous` trait still pays on a first entry and not on a repeat.
- The turn composer's prompt still lists previously-seen items (or the reason it
  no longer needs to is recorded).
- A background week at 1 and 15 min/tick is unchanged in survival, with
  Entertainment still above 0 and settling.

## Non-goals

- Any change to the novelty curve or the observation model.
- Replacing `SpatialMemory` — only its input.
