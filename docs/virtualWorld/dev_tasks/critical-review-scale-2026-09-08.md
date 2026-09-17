# Critical Review — Mujeeroth Scale Task Files vs. Real Code

**Date**: 2026-09-08  
**Scope**: task-397 through task-402, task-9, task-323, task-324  
**Method**: read the actual code paths these tasks depend on, cite line numbers, separate verified facts from inference.

---

## Executive Summary

The six world-scale tasks are architecturally reasonable in direction, but every single one depends on a serialization/identity layer that is not ready for scale. The core problem is not the tasks themselves — it's that the current code has three latent bugs that become showstoppers at million-node scale, and none of the tasks acknowledge them:

1. **`areas` dict is keyed by display name, not node ID** — two scopes both containing a "kitchen" silently overwrite each other.
2. **`Player.current_area` is a string name in 47+ references across 10 files** — cross-chunk movement requires stable node IDs.
3. **`WorldGraph.load_from_dict()` is a full clear-and-replace** — chunk loading requires a merge API that doesn't exist.

Beyond those, the trigger system, sound propagation, temperature propagation, and air propagation all do full-graph scans every tick. The editor fetches all nodes and edges and rebuilds the entire dataset on every load. None of the tasks address any of this.

---

## Verified Facts

### Serialization

**`_serialize_world` keys `areas` by `node.name`, not `node.id`**  
File: `engine/serialization.py:186`  
```python
rooms_serialized[node.name] = { ... }
```
At million-node scale, two different areas named "kitchen" in different scopes will silently overwrite each other in the save file. This is a data-loss bug, not a performance bug.

**`load_from_dict` reads both `areas` and `rooms` keys**  
File: `engine/serialization.py:337-413`  
The save format has two aliases for the same data. Any new top-level key (like `world_scopes`) must be added to both the serialization and deserialization paths, or they will diverge.

**`WorldGraph.load_from_dict()` clears the graph before loading**  
File: `graph.py:261-268`  
```python
def load_from_dict(self, data: dict):
    self.nodes.clear()
    self.edges.clear()
    ...
```
This means it cannot be used to merge a chunk into an existing graph. task-401 says "add explicit merge/unload APIs" but doesn't design them.

### Player Identity

**`Player.current_area` is a string display name**  
File: `player.py:150` (`self.current_area = None`), `player.py:724` (serialized as-is)  
47+ references across 10 files: `player.py`, `tick_manager.py`, `npc_behaviors.py`, `player_ops.py`, `movement.py`, `area_description.py`, `lighting.py`, `sound.py`, `proximity.py`, `combat.py`. Every one of these treats it as a human-readable name.

**Movement does resolve names to IDs internally**  
File: `engine/movement.py:82`  
```python
node = self.graph.get_node(self.gs._area_node_id(area_name))
```
So the engine CAN resolve names to IDs, but the player state and most call sites never use that path.

### Graph Structure

**`WorldGraph` has no edge indexes**  
File: `graph.py:130-155`  
`get_edges_for_source` and `get_edges_for_target` iterate `self.edges` linearly. For a world with millions of edges, every scope-local query scans the full list.

**`WorldGraph.add_node` auto-suffixes items/ways/characters on collision, raises on area collisions**  
File: `graph.py:71-81`  
This is fine for current scale. At million-node scale with programmatic generation, collision handling needs to be deterministic and non-raising.

### Editor Data Flow

**Editor fetches ALL nodes and ALL edges on every load**  
File: `static/js/graph/network-manager.js:128-129`  
```javascript
const nodesObj = await ApiClient.getGraphNodes();
const edgesArr = await ApiClient.getGraphEdges();
```
These hit `/api/graph/nodes` and `/api/graph/edges` which return the entire graph.

**Editor clears and rebuilds the entire vis.js dataset**  
File: `static/js/graph/network-manager.js:163-181, 282`  
```javascript
graphManager.nodes.clear();
...
graphManager.network.setData({ nodes: visNodes, edges: visEdges });
```
There is no incremental merge, no scope-aware fetch, no partial load. task-397's projection endpoints are necessary but not sufficient — the editor needs a data-flow redesign that no task file addresses.

### Trigger System

**Trigger execution does full-graph scans**  
File: `engine/triggers/execution.py`  
- Line 29: `for node in self.graph.nodes.values():` (in `_find_item_by_name`)
- Line 47: `for node in self.graph.nodes.values():` (in `_find_target_node`)
- Line 198: `[n for n in self.graph.nodes.values() if tag in ...]` (tag fan-out)
- Line 203: `for node in self.graph.nodes.values():` (name lookup)
- Line 228: `[n for n in self.graph.nodes.values() if tag in ...]` (world-scope tag scan)
- Line 253: `[n for n in self.graph.nodes.values() if n.type in match_types]` (type scan)
- Line 259: list comprehension over `self.graph.edges` (edge-type scan)

**Trigger execution has SOME null-safety**  
File: `engine/triggers/execution.py:74, 167, 440, 449`  
`self.graph.get_node()` returning None is checked in some paths. But the scans themselves are O(n) over the full graph regardless.

### Sound Propagation

**Sound source discovery iterates ALL edges**  
File: `engine/sound.py:290-322` (`get_sound_sources_in_area`)  
```python
for edge in graph.edges:
    if edge.target == area_id and edge.type == "in":
```
This scans every edge in the graph to find items in one area. At million-edge scale, this is called for every area every tick.

**Tick manager builds areas_dict from ALL nodes**  
File: `engine/tick_manager.py:712`  
```python
for node in self.graph.nodes.values():
    if node.type == "area":
        areas_dict[node.id] = node
```
Then iterates `areas_dict.items()` and calls `get_sound_sources_in_area` for each area — meaning the full-edge scan runs once per area per tick.

### Temperature and Air Propagation

**Temperature propagation iterates ALL edges**  
File: `engine/environment_propagation.py:56`  
```python
for edge in graph.edges:
    if edge.type == EDGE_CONNECTION:
```
Builds a `way_to_areas` map from the full edge list every tick.

**Heat source scanning iterates ALL nodes**  
File: `engine/environment_propagation.py:143-182` (`apply_heat_sources`)  
```python
for node in graph.nodes.values():
    if node.type != "area":
        continue
```
Then for each area, scans its `EDGE_IN` edges for heat_source items.

**Air propagation iterates ALL edges**  
File: `engine/environment_propagation.py:205-237` (`propagate_air`)  
Same pattern as temperature: full edge scan to build `way_to_areas`.

### Lighting

**Lighting queries are scoped but use linear edge scans**  
File: `engine/lighting.py:188`  
```python
for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
```
This only queries edges for one area, but `get_edges_for_source` scans the full edge list (graph.py:130-135). So it's O(areas * edges) if called for every area.

**Item light stats also use linear scans**  
File: `engine/lighting.py:116-124`  
```python
for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
```
Same issue — scoped to one area, but the underlying scan is linear over all edges.

### Delayed Events

**DelayedEventQueue stores bare node IDs with no scope info**  
File: `engine/event_queue.py:33-40`  
```python
def schedule(self, fire_tick, target_node_id, trigger_type="on_delayed", label=""):
    self.events.append({
        "fire_tick": int(fire_tick),
        "target_node_id": target_node_id,
        ...
    })
```
If the target node is in an unloaded chunk, the event cannot fire when due. There is no scope-awareness, no chunk-load-on-fire, no deferred policy.

### Background Simulation

**No background simulation code exists**  
Verified by directory listing of `engine/`: no `background_simulation.py`.  
**No `simulation_mode` field on Player**  
Verified by reading `player.py` — no such field.  
**No per-character schedule store**  
Verified — `DelayedEventQueue` is the only scheduling mechanism, and it's global/fire-and-forget.

### Pines Scenario

**`data/scenarios/pines.json` EXISTS**  
My earlier review incorrectly stated it did not. I checked `saves/` instead of `data/scenarios/`. The file contains:
- 23 areas (apartments 1a-2e, 3a, attic, hallways 1-3, main lobby, rooftop, street, downtown district, town square, suds & duds laundromat, the daily grind, vargas fitness)
- 21 players (carmen, david, deshawn, diego, erin, greg, haruka, jake, jordan, kaito, keisha, kevin, lera, mateo, maya, miki, mila, rose, taylor, valkyrie, victoria)
- All 21 players: `simple_npc: False`, `npc_behavior: wander`, no `simulation_mode`, no schedules, no background state
- 195 graph nodes, 250 graph edges
- No `world_scopes` key
- No `Apartment 3b` (must be generated)
- Uses legacy `areas` dict keyed by display name + `graph` key

**task-400's actual gap**: The scenario exists but has no scope hierarchy and no background schedules. task-399 must handle 21 LLM agents with no existing schedule infrastructure.

---

## What Is Inference vs. Verified

**Verified**: The trigger system, sound, temperature, air, and lighting all do full-graph or full-edge scans. The editor fetches everything. `current_area` is a string everywhere.

**Inference**: That these systems will "break" when chunks unload. What I actually know is that they do O(n) scans over the full graph, and if a node they expect is missing, SOME paths have null-safety (execution.py:74, 167, 440, 449) but others don't. Whether they crash, silently skip, or produce wrong results depends on the exact code path. I have not tested this.

**Inference**: That the editor "can't consume scope-aware data." What I actually know is that `loadGraphData()` fetches everything and rebuilds everything. Whether it can be modified to fetch incrementally is a frontend design question I haven't explored.

**Inference**: The exact blast radius of changing `current_area` from string to ID. I know there are 47+ references. I have not traced each one to determine if the change is trivial (just a lookup) or structural (requires changing the data model).

---

## What the Tasks Get Wrong

### task-397
- Does not address the `areas` dict name-keying bug. Adding `world_scopes` on top of a name-keyed save is building on quicksand.
- Does not specify where `world_scopes` is persisted. It's not in `_serialize_world` or `load_from_dict`.
- Does not address the editor data flow. The projection API is useless until the editor consumes it.

### task-398
- Depends on a public materialization API (`_spawn_library_item_node`) that is currently route-private. The extraction refactor is hidden inside task-9's scope.
- Does not address boundary-way mutation. Generating Apartment 3B requires modifying existing graph nodes (Hallway 3's exits). No rollback protocol.

### task-399
- Does not acknowledge that `Player` has no `simulation_mode` field, no schedule store, and no background state.
- Does not address that `tick_turn` iterates ALL players every tick with full vital decay, environmental effects, and activity processing. Background characters would still get the full treatment.
- Does not address that `DelayedEventQueue` stores bare node IDs with no scope info.

### task-400
- The Pines scenario exists (my earlier claim was wrong). The actual gap is that it has no scope hierarchy, no background schedules, and 21 LLM agents with no background infrastructure.

### task-401
- Does not define the chunk file format.
- Does not address the `current_area` string-to-ID refactor that cross-chunk movement requires.
- Does not address the global-graph-scan problem in trigger/lighting/sound/temperature/air systems.

### task-402
- Has no numbers. No payload limit, no benchmark tool, no pass/fail criterion.

---

## What Needs to Happen Before Any Task Can Start

1. **Fix the `areas` dict name-keying** — change `rooms_serialized[node.name]` to `rooms_serialized[node.id]` in `_serialize_world`. One line. Must land before task-397.

2. **Decide on `current_area` strategy** — Either: (a) keep string names and accept that cross-chunk movement requires name resolution at every boundary, or (b) refactor to `current_area_id` across 47+ call sites. This decision gates task-401.

3. **Design the chunk merge API** — task-401 says "add one" but doesn't say what it looks like. Before task-401 starts, someone needs to write the API shape: `merge_chunk(chunk_data)` → what? `unload_chunk(scope_id)` → where do characters go?

4. **Decide scope-aware strategy for global systems** — The trigger, lighting, sound, temperature, and air systems all do full-graph scans. Options: (a) make them scope-aware (only process loaded chunks), (b) keep them global but make chunk unloading a no-op for these systems, (c) replace them with indexed versions. This is a cross-cutting concern that touches 6+ engine files and should be its own task.

5. **Pick a delayed-event policy for unloaded nodes** — task-401 says "silently dropping is forbidden" but doesn't pick between: load-on-fire, park-on-chunk, or escalate. Each has different consistency implications.

6. **task-402 needs a benchmark tool and a number** — Install `pytest-benchmark` or write a custom script, and set a hard payload limit (e.g., 200KB per scope projection).

---

## What the Tasks Get Right

- task-397's `world_scopes` manifest as a top-level key is the right shape.
- task-398's `GenerationPatch` with provenance is the right design.
- task-399's `simulation_mode: active | background` distinction is clean.
- task-399's structured event log (not prose) is the right design for deterministic summarization.
- task-399's "exact/unsafe outcomes defer rather than fabricate facts" is the correct safety property.
- task-401 correctly identifies `load_from_dict()` as a clear-and-replace operation.
- task-401 correctly identifies `current_area` as a display name as unsafe for cross-chunk movement.
- The dependency chain 397→398→400 and 323→324→9→398 is correct.
