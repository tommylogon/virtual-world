# Graph System

The WorldGraph is the beating heart of VirtualWorld. **Everything** — areas, items, ways, players, characters, triggers, locations, inventories, relationships, connections — lives in this graph. If it's not in the graph, it doesn't exist in the world.

This is not a separate database or an abstract model. The graph *is* the world state. When you save, you serialize the graph. When you load, you reconstruct the graph. When a player moves, you update edges in the graph. When a trigger fires, it reads and writes node properties in the graph.

## WorldGraph: The Data Structure

Defined in `graph.py:43-168`.

```python
class WorldGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}  # node_id → Node
        self.edges: List[Edge] = []        # all directed edges
```

Two collections, that's it. A dict of nodes keyed by string ID, and a flat list of edges. No adjacency matrices, no indexing (beyond the simple filter methods). The entire world is represented as a property graph — nodes have typed properties, edges are directed with types and properties.

### Key Methods

| Method | What It Does |
|--------|-------------|
| `add_node(node)` | Insert a node; auto-suffixes on ID collision for items/ways/triggers, raises for areas |
| `remove_node(node_id)` | Delete node and all incident edges |
| `add_edge(edge)` | Insert edge; silently skips exact duplicates |
| `remove_edge(source, target, type)` | Delete matching edge |
| `get_node(node_id)` | Lookup by ID, returns Node or None |
| `get_edges_for_source(source_id, type?)` | All outgoing edges, optionally filtered by type |
| `get_edges_for_target(target_id, type?)` | All incoming edges, optionally filtered by type |
| `get_edges_by_type(type)` | All edges of a given type |
| `to_dict()` | Serialize to JSON-compatible dict |
| `load_from_dict(data)` | Deserialize from dict |
| `get_items_by_tag(tag, area_id?)` | Find item nodes with a given tag, optionally filtered by location |
| `get_characters_by_tag(tag, area_id?)` | Find player/character nodes with a given tag |
| `get_tagged_items_in_area(area_id, exclude_tags?)` | Group items in a room by tag |
| `get_items_by_tag_and_status(tag, status, area_id?)` | Find items matching both tag and current_state |
| `clear()` | Remove all nodes and edges |

## The Node Class

Defined in `graph.py:8-25`:

```python
@dataclass
class Node:
    id: str                        # Unique identifier, e.g. "area_living_area"
    type: str                      # See Node Types below
    name: str                      # Human-readable display name
    properties: Dict[str, Any]     # Free-form property bag
    created: float                 # Unix timestamp of creation
    updated: float                 # Unix timestamp of last modification
```

Every node has a `type` that determines how the engine treats it. Properties are a free-form dict — different node types expect different keys, but nothing enforces this beyond convention.

## Node Types

### `room`
Spatial locations. Players exist in areas. Items can be in areas. Rooms connect via ways.

- **Properties**: `description` (str), `environment` (dict with light/temp/air/smell/noise)
- **ID convention**: `area_lowercase_name_with_underscores`
- **Uniqueness**: Duplicate room IDs raise ValueError
- **References**: `area.py`, `engine/area_description.py`, `engine/movement.py:23-35`

### `item`
Objects that can exist in areas or in inventories. Items have `actions` (comma-separated string or array defining what you can do: examine, take, use, eat, drink, open, close), `uses` (remaining uses, -1 = infinite), `weight`, `current_state`, `description`, `tags`, `hidden` flag, and trigger-related properties.

- **Properties**: `actions`, `uses`, `weight`, `current_state`, `description`, `tags`, `hidden`, `effect_target`, `effect_stat`, `effect_amount`, `equip_slots`, `contents`, `action_costs`, `skill_check`
- **ID convention**: `item_name_with_underscores`
- **Uniqueness**: Duplicate IDs get random UUID suffix appended
- **Location**: Determined by spatial edges (`EDGE_IN`, `EDGE_ON`, `EDGE_UNDER`, etc.) — an item is "in" whatever room/container its `in` edge points to, or "carried" by whatever player its `carrying` edge points to
- **References**: `engine/item_actions.py`, `engine/effects.py`, `engine/toggleable_items.py`

### `door`
Connections between areas. Each door sits between exactly two areas via `EDGE_CONNECTION` edges. Doors have state, cost, description, pass_message, auto_close, needs_open, and trigger support.

- **Properties**: `current_state`, `description`, `cost`, `pass_message`, `auto_close`, `needs_open`, `area_from`, `area_to`, `tags`
- **ID convention**: `way_RoomName_direction`
- **Uniqueness**: Duplicate IDs get random UUID suffix appended
- **States**: open, closed, locked, blocked, broken, hidden
- **References**: `engine/movement.py:45-73`, `engine/area_description.py:37-83`

### `character` / `player`
NPCs and player characters. Graph nodes with `type="character"` represent all characters in the world regardless of whether they're player-controlled, LLM-driven, or simple NPCs.

- **Properties**: Minimal — most character data lives on the `Player` object (`player.py`), which is managed separately from the graph. The graph node primarily serves as an anchor for location edges.
- **ID convention**: `player_Name` (note: uses "player_" prefix even for characters)
- **Location**: Player's current room is tracked via `Player.current_area` string AND a location edge from the player node to the room node
- **References**: `player.py`, `engine/player_manager.py`

### `logic_trigger`
Invisible action handlers. Logic trigger nodes are never shown in the graph visualization. They exist as targets of `EDGE_TRIGGERS` edges from items, ways, and areas. Each one holds a trigger type (on_use, on_take, etc.), conditions, and effects.

- **Properties**: `trigger_type`, `effect_type`, `effect_params`, `target_name`, `conditions`, `effects`, `condition`
- **ID convention**: `trigger_parentId_type_timestamp_random`
- **Visibility**: Hidden from graph UI, managed via Inspector panel only
- **References**: `engine/trigger_system.py:760-1044`, `routes/graph.py:269-305`

## The Edge Class

Defined in `graph.py:28-41`:

```python
@dataclass
class Edge:
    source: str                    # Source node ID
    target: str                    # Target node ID
    type: str                      # See Edge Type Constants below
    properties: Dict[str, Any]     # Free-form property bag
```

Edges are **directed** — they go from source to target. This direction matters for some types (location, carried_by, unlocks) and is symmetric for others (connection). All edges in VirtualWorld are explicit — there's no implied relationship between nodes beyond what edges define.

### Edge Type Constants

Defined at `graph.py`:

```python
# ── Spatial relations (new) ──
EDGE_IN = "in"              # item/player → room/container
EDGE_ON = "on"              # item → surface/furniture
EDGE_UNDER = "under"        # item → furniture/object
EDGE_BEHIND = "behind"      # item → furniture/object
EDGE_BESIDE = "beside"      # item → furniture/object
EDGE_AT = "at"              # item/player → location/waypoint
EDGE_CARRYING = "carrying"  # item → player (inventory)
EDGE_EQUIPPED = "equipped"  # item → player (worn/held)
EDGE_GRAPPLED = "grappled"  # character → character (grappler holds target)

# ── Graph topology ──
EDGE_CONNECTION = "connection"  # room ↔ door ↔ room
EDGE_UNLOCKS = "unlocks"        # item → door
EDGE_REQUIRES = "requires"      # door → condition
EDGE_TRIGGERS = "triggers"      # node → logic_trigger
```

All edges follow a consistent direction: **source is the thing being positioned, target is the location/surface/owner**.

#### `in` — Primary location edge
The spatial home for items and characters. Replaces the old `location` (item→room/player) and `contains` edges.

- `item → room`: Item is sitting in that room
- `item → container_node`: Item is inside that container
- `character → room`: Character is in that room
- Room descriptions use `get_edges_for_target(area_id, EDGE_IN)` to find items in a room
- Container contents use `get_edges_for_target(container_id, EDGE_IN)` to find items inside

#### `carrying` — Inventory edge
An item is carried by a player. Replaces the old `carried_by` and `location` (item→player) edges.

- `item → player_node`: Item is in that player's inventory — *not* in the room
- This is how `get_area_items()` filters out carried items: they're on the player, not the room

#### `equipped` — Equipment edge
An item is worn or held in a body slot. Edge properties include `slot` and `order`.

#### `on` / `under` / `behind` / `beside` — Spatial refinements
Finer-grained positioning relative to furniture/objects. Defined for future `examine` enrichment — currently not queried in engine code but available through the graph API and UI.

#### `connection` — Room-to-door links
Area-to-door-to-room links. Always four edges per bidirectional connection (room → door, door → other_area, other_area → door, door → room).

**Direction property**: Each connection edge has a `"direction"` property (e.g. `"north"`, `"front door"`, `"enter"`). This maps typed directions to graph edges. The `"enter"` direction appears on door→room edges (the direction you're going when you walk through).

**visible_in_direction property**: Optional string on room→door edges that provides a "what you see beyond" preview when the door is open.

#### `unlocks` — Key relationships
Item-to-door key relationships. Source is an item node, target is a door node. When a player uses the key item on the door, the engine checks for unlock edges. Being replaced by triggers but still supported.

#### `requires` — Door gating
Links a door to a condition node. A door that requires certain conditions to be met before it can be opened.

#### `triggers` — Action handlers
Links an item, door, or room to a `logic_trigger` node. Trigger edges and their target nodes are hidden from the graph UI.

```python
triggers = self.graph.get_edges_for_source(item_node.id, EDGE_TRIGGERS)
```

The trigger edge itself carries properties (`trigger_type`, `conditions`, `effects`, etc.). Properties-on-edge is the preferred approach for new triggers.

#### Backward Compatibility

Old edges (`location`, `carried_by`, `contains`) are **automatically migrated** on load via `WorldGraph.load_from_dict()` → `normalize_edges()`:

| Old | New | Direction |
|-----|-----|-----------|
| `location` (item→room) | `in` | Same |
| `location` (item→player) | `carrying` | Same |
| `location` (player→room) | `in` | Same |
| `carried_by` (item→player) | `carrying` | Same |
| `contains` (item→container) | `in` | Same |

Query backward compat: `get_edges_for_target(area_id, "in")` also matches old `"location"` and `"contains"` edges via `resolve_edge_types()`. Old engine code that still uses `EDGE_LOCATION` / `EDGE_CARRIED_BY` / `EDGE_CONTAINS` will continue to work until fully migrated — but all engine code has been updated to the new constants.

## How the Graph Stores All World State

The graph isn't one view of the world — it's the authoritative source for everything:

### Area State
Area nodes hold descriptions and environments. The `RoomDescription` class (`engine/area_description.py`) reads `graph.nodes` to find areas, `graph.edges` to find items/players/exits in each room. The `Area` object (`room.py`) is a compat layer — the graph is the real source of truth.

### Player Location
Each player character has a graph node (`player_Name`) and a location edge to their current room. The `PlayerManager` keeps a `Player.current_area` string for quick access, but the graph edge is the canonical location. On deserialization (`engine/serialization.py:177`):

```python
if p.current_area:
    self.player_manager.set_player_area(pname, p.current_area)
```

This creates or updates the location edge from the player node to the room node.

### Item Locations
Every item has at least one spatial edge (`in`, `carrying`, `on`, etc.) pointing to its location. Most items have one `in` edge (to a room or container) — unless they're being carried (`carrying` edge to player). Moving an item means deleting the old spatial edge and creating a new one. The `/api/graph/item/<id>/move` endpoint (`routes/graph.py:61-...`) handles this. It accepts `area`, `container`, **or `character`** — a character destination creates a `carrying` edge to the character node (the item inspector's **Move To → Character** / "Give To" radio, `inspector/item-view.js`), removing any previous placement. The endpoint validates that the target node is a `character`/`player` node and returns 404 for unknown targets.

### Way States
Way nodes hold `current_state`. This is the single source of truth — both areas "see" the same door node, so there's no sync issue. When a player opens a door from the Living Area side, the same door is open from the Study side too. Way operations just update `way_node.properties["current_state"]` on the shared node.

### Triggers
Trigger edges form a graph within the graph. Items, ways, and areas point to `logic_trigger` nodes, which hold condition/effect data. The trigger edges are filtered out of the visual graph but are fully functional in the engine.

### Inventory
Items carried by players have `carrying` edges from the item node to the player node. The `get_inventory()` methods scan `get_edges_for_target(player_id, EDGE_CARRYING)` for item nodes. Container contents use `in` edges pointing to the container node — same as items in rooms use `in` edges to the room.

### Equipment
Equipment items have `equipped` edges from the item node to the player node, with a `slot` property on the edge. The `Player.equipped` dict (slot → item IDs) is derived from these edges, with `_sync_equipped_from_graph()` to recover from desync. This is a hybrid approach — the graph edge is the canonical source of truth, the dict is the fast-access cache.

## Graph Visualization in the UI

The graph is rendered using **vis-network** (vis.js) in the browser. The frontend graph module lives in `static/js/graph/`, one file per concern (the full, generated list is `docs/design/js-module-index.md`):

| File | Purpose |
|------|---------|
| `network-manager.js` | vis.js setup, data loading, tooltips, legend, physics, filtering, overlays |
| `relative-layout.js` | **Derive** node positions from relations (orbit, follow, levels, per-node controls) — see [Derived layout](#derived-layout-relative-layoutjs) |
| `separation.js` | Short-range relaxation: push nearby unconnected nodes apart (items/characters stop overlapping), grid-bounded |
| `context-menu.js` | Right-click context menus for nodes and edges |
| `layout-engine.js` | Cardinal direction layout algorithm (map mode only) |
| `tree-view.js` | World outline tree rendered in the left panel (Outline tab); click-to-focus camera |
| `node-operations.js` | Node creation, editing, deletion, duplication |
| `event-handlers.js` | Click, double-click, drag handlers |
| `graph-background.js` | Map background layers (images beneath the nodes) |

### Node Visualization by Type

From `network-manager.js:57-63`:

| Type | Shape | Background | Border | Font |
|------|-------|-----------|--------|------|
| room | box | `#2d333b` | `#58a6ff` | `#c9d1d9`, 14px |
| item | diamond | `#3d2e1a` | `#e3b341` | `#e3b341`, 12px |
| door | triangle | `#1a3a2a` | `#4ec9b0` | `#4ec9b0` |
| character | ellipse | `#2a1a3d` | `#bc8cff` | `#bc8cff`, 14px |

### Edge Visualization by Type

| Type | Color | Dashed | Label |
|------|-------|--------|-------|
| connection | `#4ec9b0` (teal) | No | (none) |
| in / carrying / on / under etc. | `#484f58` (gray) | No | (type name) |
| unlocks | `#3fb950` (green) | Yes | "unlocks" or custom |

Trigger edges (`EDGE_TRIGGERS`) and logic trigger nodes are **excluded** from the visual graph entirely (`network-manager.js:103` and `:153`):

```javascript
if (nodeData.type === 'logic_trigger') continue;
if (edgeType === 'triggers') continue;
```

### State-Based Coloring

Doors change color based on `current_state` (`network-manager.js:116-131`):
- **open**: green border (`#3fb950`)
- **closed**: amber border (`#e3b341`)
- **locked**: red border (`#f85149`)
- **hidden**: gray border (`#6e7681`)
- **blocked**: orange border (`#f0883e`)
- **broken**: red border (`#f85149`)

Items change color based on state (`network-manager.js:133-142`):
- **lit**: orange border (`#f0883e`)
- **broken**: gray border (`#6e7681`)
- **depleted**: brown border (`#8b7355`)

### Graph Physics

The graph uses vis.js's force-directed layout with `forceAtlas2Based` solver (`network-manager.js`,
`buildOptions()`):

```javascript
physics: {
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
        gravitationalConstant: -8,   // repulsion between nodes
        centralGravity: 0.05,        // the free layout's pull toward the origin
        springLength: 120,
        springConstant: 0.1,
        damping: 0.4
    }
}
```

**`centralGravity` follows the layout.** It is a graph-wide field applied to every node on every solver
iteration and vis exposes no per-node or per-mode control for it, so it is pushed as a value on every
switch. The rule lives in one function, `GraphNetwork.centralGravityFor(layout)`, and every layout
switch goes through `GraphNetwork.applyModePhysics(enabled)` so no call site can re-decide it:

| Layout | `centralGravity` | why |
|---|---|---|
| **🔮 Graph** | **0.05** (barnesHut: 0.3) | the free force layout has nothing else holding it together — with 0 a component not edge-connected to the rest of the world drifts off, and a measured cold load grew +9000 px of width per 40 s |
| **🗺️ Map** | **0** | the painted lattice *is* the map and areas are pinned to their cells, so a pull toward the canvas origin fights the art — and a room's contents are held by their own `in` edge spring instead |
| **🌳 Levels** | **0** | vis's hierarchical layout owns positions and forces physics off, so it is never read; it is set anyway so switching back does not inherit a number chosen for a layout that was not running |

0.05 is the *smallest* value that holds the graph, measured on `kraktooth_goblin_camp` (638 nodes, all
floating in the graph view): 0 runs away, 0.05 settles flat at 1209 px of width, 0.2 settles at 984 px,
0.6 crushes it to 890 px. **barnesHut's 0.3 is its historical default and was not re-measured**; the two
solvers are not on the same scale.

The repulsion/spring numbers above are the balance measured for **Map** mode (gravity 0, areas pinned);
they are shared with the graph view, where nothing is pinned. Physics can be toggled on/off. Nodes can
have `central_gravity_enabled: false` to lock their position. The graph uses signature-based
deduplication to avoid jitter on tick updates — only reloads the vis.js data when the graph structure
actually changes.

> **Known gap — a content whose room is frozen has no anchor.** vis does not apply spring forces to a
> node with `physics: false`, so a simulated item/character/trigger whose parent is *excluded* from
> physics is held by nothing: gravity and repulsion only. Measured on `kraktooth_goblin_camp` in the
> graph layout, **48 of 48** content↔room pairs are of this kind (the scenario freezes 31 of its 206
> areas, and they are the ones with contents), and those contents settle a **median 3185 px** (max
> 5004 px) from their room with the solver reporting `stabilized: true` — so it never self-corrects.
> Map mode is unaffected (the grid pass places each content beside its area and nothing travels far),
> which is why this only shows in the free graph layout. The fix is not a gravity value: a content
> belongs in the solver only when its parent is. That is not implemented yet.

### Physics settings (Settings → Graph)

`graph/network-manager.js::buildOptions()` reads `config.graph*` and injects them into the solver.
The sliders in **Settings → Graph** map directly:

| Setting | Config key | Solver param | To make connected nodes **tighter** |
|---------|-----------|--------------|-------------------------------------|
| Spring Length | `graphSpringLength` | `springLength` | lower (e.g. 40–60) |
| Repulsion | `graphGravitationalConstant` | `gravitationalConstant` | toward **Weak** (less negative) |
| Damping | `graphDamping` | `damping` | higher (Stiff) so it settles |
| Spring Stiffness | `graphSpringConstant` | `springConstant` | **higher** (Rigid) — the main "hold connected together" lever |
| Physics Solver | `graphSolver` | `solver` | `forceAtlas2Based` (default) or `barnesHut` |

**Important:** these only apply in **Graph (🔮)** mode. The **🗺️ Map / cardinal layout** bypasses them
entirely — `applyCardinalLayout()` hardcodes its own `barnesHut` physics and force-places items and
characters on a fixed grid. If you tweak the sliders and see no change, you're in Map mode.

**They govern a room's contents too, and how far they start out.** The sliders are the solver's
balance, and everything in the graph is in the solver — areas, ways, items, characters and triggers.
**Item Edge Length** and the per-node overrides in the inspector are separate: they scale the ring a
room's contents are *seeded* onto, not a distance the solver maintains.

### Derived layout (`relative-layout.js`)

A saved snapshot of every node's `x`/`y` is stale the moment anything is created or deleted, and it
never explained *why* a node sat where it did. The layout is therefore **derived from the relations**
and re-derived, not restored:

- **Parent selection** uses a priority: `carrying` > `equipped` > `at` > `in` > `triggers`. A room's
  item, a carried item and an equipped item each resolve to the right anchor; a mixed `in` group's
  direction is resolved by depth from the area roots.
- **Contents orbit their parent** instead of stacking on its label. The ring radius grows with the
  crowd (`ORBIT`: `minRadius` 130, `maxRadius` 320, `spacing` 92, `baseEdgeLength` 60,
  `nestedScale` 0.45). Ways sit at the **midpoint** of their two rooms and are placed first.
- **Explicit distances are exact** — a `layout_distance`/`layout_child_distance` pins the offset even
  if labels then overlap. The comfort floor/cap and crowd-spacing growth apply only to *inherited*
  distances.
- **The ring is a seed, and the solver owns the node afterwards.** `apply()` places each child on its
  parent's ring once and hands it over with `{fixed:false, physics:true}`. This used to be impossible:
  vis-network's `centralGravity` is a *global field* applied to every node on every solver iteration, and
  the edge spring cannot outvote it, so contents were kept out of the solver
  (`{fixed:false, physics:false}`) and held on a parent-relative offset by a **follow pass** re-applied
  every 120 ms. **`centralGravity` is now `0` in Map and Levels** (see
  [Graph Physics](#graph-physics)), which removes the field the whole arrangement existed to fight — so
  the follow pass and its live separation easing are gone, and nothing re-places a child after the seed.
  Dragging a room no longer yanks its contents back onto the ring on drop; the edge spring carries them.
  In the **graph** layout gravity is back on (0.05) — but see the known gap above: a content whose room
  is frozen from physics has no spring to hold it, so it drifts.
- **The spring/repulsion balance is what replaced it.** With no central pull, repulsion is the only
  thing pushing, and the old forceAtlas2 numbers lost: a cold load of `kraktooth_goblin_camp` (638
  nodes) grew **+4069 px of width per 12 s** and left contents a **median 888 px** from the room
  holding them. Repulsion `-8` / spring constant `0.10` / spring length `120` (`config.js` defaults,
  overridable in Settings) puts contents **beside** their rooms — measured cold in Map mode: median
  **135 px**, p90 **208 px**, and **0** content pairs overlapping.
- **Short-range separation** (`graph/separation.js`, setting `graph_repel_enabled`) is now a **seed
  pass only**: it de-overlaps the ring `layoutPositions` derives, so a crowded room or a nested
  container does not start life layered on top of itself. Two nodes closer than **Repel Distance**
  (`graph_repel_min`, default 55) push apart, a pair further than **Ignore Beyond**
  (`graph_repel_max`, default 220) is ignored, and a pair joined by **any edge** is exempt — a container
  and its contents (or an item and its carrier) are meant to touch. **Parent Pull** (`graph_repel_pull`,
  default 0.12) is a restoring force back to a node's **own ring position** — never the parent's centre,
  which would suck a crowded character/item onto the area it belongs to — applied only to nodes
  separation actually displaced. It no longer runs during simulation: repulsion is what keeps contents
  apart once they are in the solver. A uniform grid keyed by `max`-sized cells keeps it ~linear; areas
  and ways are anchors and never move, and a frozen node keeps its place. The push target is
  `max(min, r1 + r2)`, where the radii grow with the name so long labels get room.
- **Item Edge Length** and the per-node `layout_*` numbers scale the **seed ring**; changing a physics
  setting calls `reseed()` so the arrangement re-derives on the next layout. A frozen node dropped by
  hand keeps its place across reloads (`frozenDropOps`).

**Levels mode.** The toolbar's **🌳 Levels** button (config `graph_layout_mode`) hands the graph to
vis's hierarchical solver for an outline-like view (`levelSeparation` 150, `nodeSpacing` 110,
`treeSpacing` 170, physics forced off). Switching back to free physics does so cleanly — four silent
re-enablers had to be fixed (`applyCardinalLayout`, `graph-background._applyLockState`, the persisted
`graph.physics_enabled` load/switch paths, `_clearOverlay`).

**Per-node physics (`layout_*` properties).** Precedence is **child → parent → global**, editable from
the inspector's **Graph Physics** section (`H.setLayoutNumber` in `static/js/inspector/helpers.js`):

| Property | On | Effect |
|----------|----|--------|
| `layout_static` | any node | freeze this node (`physics: false`) |
| `layout_distance` / `layout_child_distance` | item / parent | exact distance from the parent (px) |
| `layout_child_spacing` | parent | desired gap between its contents (px) |
| `layout_min_radius` / `layout_max_radius` | parent | clamp the orbit ring (px) |

### Edge dedup & suppression (character↔item)

The backend can emit **three** edges for the same item↔character link (`carrying`, `equipped`, and a
stray `connection`). `graph/network-manager.js::loadGraphData()` suppresses the redundant ones at
render time:

- **`connection` edges between a character and an item are never drawn** (the backend sometimes emits
  one alongside carrying/equipped).
- **`carrying` is suppressed when the same item↔character pair already has an `equipped` edge** — so an
  equipped item shows one `equipped` edge, and a plainly carried item shows one `carrying` edge.

The result: exactly one edge per character→item link — `equipped` if worn/held, `carrying` if just in
inventory, never `connection`.

### Cardinal Layout (🗺️ Map button)

The toolbar's **🗺️ Map** button toggles a cardinal-direction-based grid layout on the vis.js graph. This positions rooms geographically — areas to the north get placed above, areas to the east to the right, etc. -- creating a top-down map feel without switching to a separate view.

**What gets positioned:**

| Element | Placed | Physics? |
|---------|--------|----------|
| **Area nodes** | BFS grid based on exit cardinals | ❌ pinned, `fixed` |
| **Way nodes** | Midpoint between their two connected rooms | ✅ simulated, settles via edge |
| **Item nodes** | Seeded beside their parent room (derived ring) | ✅ simulated, held by the `in` edge |
| **Character nodes** | Seeded beside their current room (derived ring) | ✅ simulated, held by the `in` edge |

**Per-node physics:** Areas are pinned to their cells, because the cells *are* the
map and the background art is drawn to them. Ways are deliberately **simulated**: the
layout places no way nodes of its own, so without the solver they pile up wherever
they were last saved and every edge then crosses the whole map (task-530). Items and
characters are simulated as well, seeded beside their room by the derived layout and
then held there by their own `in` edge spring — which only works because the solver has
no `centralGravity` (see [Graph Physics](#graph-physics)); with it on, a node left in
the solver is dragged off its parent no matter how stiff the edge. An author-frozen
node (`central_gravity_enabled: false`, the inspector's "Physics enabled") keeps
physics off whatever its type.

**Two coordinate spaces.** `properties.x`/`y` is overloaded, and `properties.cell`
is what tells them apart:

- **Engine units** — the WorldPainter compiler writes `cell * 40`, and the map layout
  scales them by the map pitch and translates them by the scope's `map_offset`
  (task-523). The compiler stamps `cell` on **areas and ways** so these are
  recognisable; a way's `cell` is the half-integer midpoint of the two cells it joins.
- **Canvas pixels** — a node dragged in the graph stores where it was dropped, and
  the map layout uses it verbatim. Characters and items are always in this space.

`map_offset` is a *render-time* translation and is never written back into stored
coordinates. Saving a layout must therefore skip painted nodes: writing canvas pixels
over engine units would rescale them on the next layout *and* re-add the scope offset,
so the node would creep further away on every save. Use
`GraphLayoutEngine.hasPaintedCoords(props)` for that check rather than a bare
`props.cell` test, which silently misses ways and characters.

**Two guards (bug-45):** the cardinal layout only auto-moves nodes in **map mode** — in graph/manual
view, hand-placed nodes stay where they were put — and a **frozen** node
(`central_gravity_enabled: false`) is skipped even in map mode, so a pin survives a layout pass.

**Setting cardinals on ways:** Open a way's inspector (`Connections` section). The Cardinal dropdowns for A→B and B→A are linked — selecting "east" for A→B automatically sets B→A to "west". When a cardinal changes, the graph layout updates live.

### Legend

The graph has a toggleable legend overlay (`network-manager.js:276-292`) showing node type shapes, door state colors, and item state colors.

### Inspector Integration

Clicking a graph node opens the Inspector panel (`context-menu.js:83`):
```javascript
VW?.inspector?.showNode(target.nodeId);
```

Right-click provides context actions:
- Rooms: Add Item, Move Character, Create Character, Add Trigger Edge
- Items: Edit, Save to Library, Add Trigger Edge, Delete
- Doors: Edit, Add Trigger Edge, Delete
- Characters: Edit, Add Trigger Edge
- All: Inspect, Duplicate, Show in Library

## Node ID Conventions (Summary)

From `engine/node_ids.py` and `AGENTS.md:67-75`:

| Type | Pattern | Example |
|------|---------|---------|
| room | `area_<lowercase_name>` | `area_living_area` |
| item | `item_<name>` | `item_rusty_key` |
| player/character | `player_<Name>` | `player_Traveler` |
| door | `way_<RoomName>_<direction>` | `way_Kitchen_west` |
| logic_trigger | `trigger_<parent>_<type>_<ts>` | `trigger_rusty_key_on_use_1234` |

## API Endpoints for Graph Operations

All graph CRUD goes through `routes/graph.py` (`/api/graph/...`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/graph/nodes` | GET | Get all nodes |
| `/api/graph/edges` | GET | Get all edges |
| `/api/graph/node` | POST | Create node |
| `/api/graph/node/<id>` | PATCH | Update node properties |
| `/api/graph/node/<id>` | DELETE | Delete node |
| `/api/graph/node/<id>/rename` | POST | Rename node ID |
| `/api/graph/item/<id>/move` | POST | Move item to room/container |
| `/api/graph/edge` | POST | Create edge |
| `/api/graph/edge` | DELETE | Delete edge |
| `/api/graph/edge/update` | POST | Update edge type/properties |
| `/api/graph/door/reconnect` | POST | Rewire door to different areas |

Plus legacy build endpoints that are kept for backward compat:
| `/api/build/room` | POST | Create/update room |
| `/api/build/item` | POST | Create/update item with triggers |
| `/api/build/connect` | POST | Connect areas with door |

## Serialization

The graph serializes via `WorldGraph.to_dict()` and `WorldGraph.load_from_dict()` (`graph.py:88-92` and `161-167`):

```python
def to_dict(self) -> dict:
    return {
        "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        "edges": [e.to_dict() for e in self.edges]
    }
```

This is embedded in the larger world state dict produced by `WorldSerializer.to_dict()` (`engine/serialization.py:84`):

```python
"graph": self.graph.to_dict(),
```

On load (`serialization.py:109-112`):
```python
if "graph" in data:
    self.graph.load_from_dict(data["graph"])
else:
    self._build_graph_from_legacy(data)
```

The legacy path handles old-format data (areas/items dicts without a graph key) by reconstructing the graph from scratch.

## Graph Integrity Rules

While the engine doesn't enforce these at the graph level (no constraint system), they're critical conventions:

1. **Every room needs at least one door to be reachable** (unless it's the starting room)
2. **Every door connects exactly two areas** — four connection edges total
3. **Every item has at least one spatial edge** (`in`, `carrying`, `on`, etc.) to its location
4. **Every player/character has exactly one `in` edge** to their current room
5. **Trigger edges always point to logic_trigger nodes**
6. **Way current_state is the authoritative state** — checked on every movement attempt
7. **Area names are unique** — enforced at `add_node()` time

## The Node ID Rename Operation

One of the trickier operations is renaming a node ID (`routes/graph.py:96-124`). It:
1. Creates a new node with the desired ID, copying all properties
2. Iterates all edges, updating source/target from old ID to new ID
3. Removes the old node

This is inherently risky if the new ID collides with an existing node (checked before proceeding) or if something holds a reference to the old ID string. But within the graph system itself, it works atomically.

## Graph as Game Loop Backbone

The game loop engine (`virtual_world_engine.py`) delegates to 22 engine modules, and nearly all of them read/write the graph:

- **Movement**: Reads connection edges, updates door node states
- **Area descriptions**: Reads room nodes, item location edges, connection edges
- **Triggers**: Reads trigger edges, creates/modifies nodes and edges as effects
- **Lighting**: Reads connection edges to find open ways for light spill
- **Combat**: Reads character location edges for targeting
- **Item actions**: Reads item nodes and their properties
- **Toggleable items**: Modifies room environment properties
- **Serialization**: Reads/writes the entire graph

The graph pattern means you can add new node types, edge types, or properties without schema migrations — just start writing and reading the new keys. It's flexible, but it means there's no compile-time checking that a room has a `description` or a door has a `current_state`. Those are conventions enforced by the engine code, not the data structure.

## Map backgrounds

A scenario can carry any number of reference images (a regional map, a floor plan, a
sketch) drawn beneath the node graph. Right-click empty canvas → 🗺 to add one. All the
arranging happens **above** the canvas, because the images paint in a layer beneath it
and the vis canvas owns pointer events - nothing under the canvas can be clicked.

### Storage

The scenario block `graph_background` holds:

    graph_background:
      layers:
        - id: bg-xxxxxxx        # stable per layer and across relayouts
          label: Ground floor
          image: /static/images/backgrounds/floor-1.png   # or a data: URL fallback
          rect: { x, y, width, height }                   # graph space
          rotation: 0            # degrees
          crop: { x, y, w, h }   # normalised source window
          opacity: 0.45
          locked: false          # this image cannot be dragged
          visible: true
      positions: { nodeId: { x, y } }    # captured node layout
      layoutLocked: false                # node physics freeze

- Images are stored as **files** under `static/images/backgrounds/` and referenced by
  path, so a multi-megabyte map never becomes base64 inside the scenario JSON. Only an
  image whose upload failed falls back to a data URL in the block.
- **Array order is z-order**: later layers draw on top.
- `layoutLocked` is the old single-image `locked` (freeze node physics, apply the saved
  positions). A legacy `{ image, rect, ... }` block migrates to a one-layer list on load,
  and `locked` maps to `layoutLocked`, not to a layer lock.
- Local fallback is the IndexedDB store `graph_assets`, keyed by the scenario name. The
  world/file copy always wins; the cache only covers images never uploaded. An **empty
  layer list means "no maps" and must clear the screen** - collapsing that into "no
  record" was bug-39.

### Arranging

| Action | How |
|---|---|
| Select | click a map (topmost wins); **alt-click** cycles down through the stack |
| Move | drag it; hold alt or shift to bypass snapping |
| Scale | the corner handles; shift keeps the aspect ratio |
| Rotate | the purple top dot; shift snaps to 15° |
| Crop | ✂ Crop, then drag the amber inner handles |
| Nudge | arrow keys (shift = 10 units) |
| Opacity | the 🎚 slider in the on-canvas hint |
| Order, visibility, lock, rename, delete | the layer panel, top right while editing |
| Fit one layer to the nodes | right-click → ⤢ Fit to nodes |
| Save the node layout | right-click → 💾 Save layout to world (one batched undo step) |

Snapping pulls a layer's edges and centre onto the other layers and the node bounds, so
two maps can be lined up without fighting the mouse. Handles are counter-scaled to a
constant on-screen size, so they stay clickable when zoomed out.

## Related tasks

- [[dev_tasks/inprogress/graph/task-451-multiple-background-images-per-scenario-with-easy-placement-and-layering|task-451: Multiple background images per scenario]]

- [[task-100-graph-view-filters|task-100: Graph view filters]]
- [[dev_tasks/done/graph/task-105-edge-refactor|task-105: Edge refactor (done)]]
- [[dev_tasks/done/archive/task-82-map-view-and-directions|task-82: Map view and directions]]
- [[dev_tasks/review/graph/task-35-graph_visual_alternatives|task-35: Graph visual alternatives]]
- [[dev_tasks/review/graph/task-40-per_node_graph_gravity_toggle|task-40: Per-node graph gravity toggle]]
- [[dev_tasks/review/graph/task-46-room_tree_view|task-46: Area tree view]]
