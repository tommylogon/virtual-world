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

The graph is rendered using **vis-network** (vis.js) in the browser. The frontend graph module lives in `static/js/graph/` with seven files:

| File | Purpose |
|------|---------|
| `network-manager.js` | vis.js setup, data loading, tooltips, legend, physics, filtering, overlays |
| `context-menu.js` | Right-click context menus for nodes and edges |
| `layout-engine.js` | Cardinal direction layout algorithm |
| `tree-view.js` | World outline tree rendered in the left panel (Outline tab); click-to-focus camera |
| `node-operations.js` | Node creation, editing, deletion, duplication |
| `event-handlers.js` | Click, double-click, drag handlers |

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

The graph uses vis.js's force-directed layout with `forceAtlas2Based` solver (`network-manager.js:45-48`):

```javascript
physics: {
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
        gravitationalConstant: -40,
        centralGravity: 0.005,
        springLength: 100,
        springConstant: 0.02,
        damping: 0.4
    }
}
```

Physics can be toggled on/off. Nodes can have `central_gravity_enabled: false` to lock their position. The graph uses signature-based deduplication (`network-manager.js:78-89`) to avoid jitter on tick updates — only reloads the vis.js data when the graph structure actually changes.

### Cardinal Layout (🗺️ Map button)

The toolbar's **🗺️ Map** button toggles a cardinal-direction-based grid layout on the vis.js graph. This positions rooms geographically — areas to the north get placed above, areas to the east to the right, etc. -- creating a top-down map feel without switching to a separate view.

**What gets positioned:**

| Element | Placed | Frozen? |
|---------|--------|---------|
| **Area nodes** | BFS grid based on exit cardinals | ✅ physics off, fixed |
| **Way nodes** | Midpoint between their two connected rooms | ✅ physics off, fixed |
| **Item nodes** | Scattered below their parent room (3-column grid) | ❌ physics on, settles via edge |
| **Character nodes** | Stacked to the right of their current room | ❌ physics on, settles via edge |

**Per-node physics:** Areas and ways use `physics: false` + `fixed: {x: true, y: true}` so they stay frozen in place. Items and characters use `physics: true` (default) — they settle naturally via their `location` edge springs while the layout is active.

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

## Related tasks

- [[task-100-graph-view-filters|task-100: Graph view filters]]
- [[dev_tasks/done/graph/task-105-edge-refactor|task-105: Edge refactor (done)]]
- [[dev_tasks/done/archive/task-82-map-view-and-directions|task-82: Map view and directions]]
- [[dev_tasks/review/graph/task-35-graph_visual_alternatives|task-35: Graph visual alternatives]]
- [[dev_tasks/review/graph/task-40-per_node_graph_gravity_toggle|task-40: Per-node graph gravity toggle]]
- [[dev_tasks/review/graph/task-46-room_tree_view|task-46: Area tree view]]
