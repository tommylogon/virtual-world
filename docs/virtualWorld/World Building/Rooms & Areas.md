# Rooms & Areas

Rooms are the spatial atoms of VirtualWorld. Every room is a `room`-type node in the WorldGraph, and every player/character has exactly one `current_area` at any given time. Existence happens in a room.

## Area Nodes

Each room lives as a `Node` in the WorldGraph with `type="room"`. The dataclass is defined in `graph.py:8-25`:

```python
@dataclass
class Node:
    id: str          # e.g. "area_living_area"
    type: str        # "room"
    name: str        # Human readable, e.g. "Living Area"
    properties: Dict[str, Any]  # description, environment
    created: float   # timestamp
    updated: float   # timestamp
```

Rooms are created via `MovementSystem.add_area()` in `engine/movement.py:23-35`. The method takes a `Area` object (from `room.py`), generates a node ID, and stores the description + environment dict as properties.

### Node ID Conventions

Area node IDs follow a strict convention defined in `engine/node_ids.py:16-24`:

```python
@staticmethod
def area_node_id(name: str) -> str:
    safe = name.lower().replace(" ", "_")
    return f"area_{safe}"
```

So `"Living Area"` → `"area_living_area"`. Kitchen → `area_kitchen`. This convention is used across every engine module that needs to look up a room by name — `movement.py`, `area_description.py`, `serialization.py`, `routes/graph.py`, etc. The `NodeIDHelper` class is imported as part of `VirtualWorld` (which has `_area_node_id()` wrappers).

**Important**: Area node IDs must be unique. The `WorldGraph.add_node()` method (`graph.py:49-60`) raises `ValueError` if you try to add a room with a duplicate ID:

```python
def add_node(self, node: Node):
    if node.id in self.nodes:
        if node.type in ('item', 'door', 'logic_trigger'):
            suffix = str(uuid.uuid4())[:8]
            node.id = f"{node.id}_{suffix}"
        elif node.type == 'area':
            raise ValueError(f"Area node '{node.id}' already exists.")
```

Only areas get the hard uniqueness check — items, ways, and logic triggers get auto-suffixed on collision.

### Area Name vs Node ID

The `name` field is the human-readable display name (e.g. `"Living Area"`), while `id` is the machine-friendly lookup key (e.g. `"area_living_area"`). The serialization system (`engine/serialization.py:58-69`) reconstructs the areas dict from graph nodes by iterating `graph.nodes` and filtering for `type == "room"`, using `node.name` as the dict key:

```python
for node in self.graph.nodes.values():
    if node.type == "area":
        rooms_serialized[node.name] = {
            "name": node.name,
            "description": node.properties.get("description", ""),
            "environment": node.properties.get("environment", {}),
            "exits": self.player_manager.build_exits_for_area(node.name),
            ...
        }
```

## Area Properties

The `properties` dict on a room node contains two critical keys: `"description"` and `"environment"`.

### description

A free-text string used as the room's primary description. Displayed via `RoomDescription.get_area_description()` in `engine/area_description.py:85-312`. This is the main "you are here" text shown when a player looks around.

### environment

An `environment` dict nested inside properties holds the room's environmental state. Default values (from `room.py:8-14`):

```python
{
    "light": 80,       # 0-100 numeric, or string enum
    "temperature": 21,  # celsius
    "air": "fresh",     # fresh, stale, toxic, smoky, humid, fragrant, cold, damp, musty, dusty
    "smell": "neutral", # free-text or "neutral"/"fresh"
    "noise": "quiet"    # quiet, silent, loud, chaotic, or free-text
}
```

These are set when creating a room via `routes/graph.py:163-187` (the `/api/build/room` endpoint) or from the world template.

#### Light

Light is numeric 0-100. The `LightingSystem` in `engine/lighting.py` converts it to a five-level enum via `light_to_level()`:

| Range  | Level        | Effect |
|--------|-------------|--------|
| ≤20    | pitch_black | Cannot see, examine, take, or use. Sanity decays -1/tick. |
| ≤40    | dim         | Barely see shapes, dim description shown. |
| ≤70    | normal      | Normal visibility. |
| ≤90    | bright      | — |
| >90    | blinding    | — |

The conversion happens in `engine/lighting.py:13-30`:

```python
def light_to_level(self, value):
    try:
        v = int(value)
    except (ValueError, TypeError):
        if isinstance(value, str) and value in ('pitch_black', 'dim', 'normal', 'bright', 'blinding'):
            return value
        return 'normal'
    if v <= 20: return 'pitch_black'
    elif v <= 40: return 'dim'
    elif v <= 70: return 'normal'
    elif v <= 90: return 'bright'
    else: return 'blinding'
```

Light can also be specified as string enums in data (e.g. `"light": "dim"`). The `get_light_int()` method (`engine/lighting.py:32-39`) handles both formats, mapping strings back to integers:

```python
mapping = {'pitch_black': 10, 'dim': 30, 'normal': 55, 'bright': 80, 'blinding': 95}
```

#### Light Spill Between Rooms

The clever bit: light spills through open ways. `get_ambient_light()` in `engine/lighting.py:41-65` computes the effective light for a room by checking all open ways to adjacent areas and taking `max(own, best_spill)` where spill = `int(adjacent_light * 0.5)`:

```python
for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
    door = self.graph.get_node(edge.target)
    if door and door.type == "door" and door.properties.get("current_state") == "open":
        ...
        spill = max(0, int(o_light * 0.5))
```

This means a dark room connected to a brightly lit room via an open door gets half the adjacent room's light. Close the door and the spill disappears — the room goes dark again.

The light spill notification is rendered in `RoomDescription.get_area_description()` (`engine/area_description.py:103-123`):

```
Bright light spills in from the Living Area through the open east.
```

#### Temperature

Temperature is in Celsius. The room description system (`engine/area_description.py:141-175`) interp rets it with a free-text summary:

| Range   | Description |
|---------|------------|
| ≥35     | "The scorching heat is overwhelming." |
| ≥30     | "It's quite hot here." |
| ≥25     | "It's warm." |
| 11-24   | (no summary) |
| 1-10    | "It's cold." |
| ≤0      | "It's freezing cold." |
| ≤-5     | "It's bitterly cold." |

**Warning system** (`engine/area_description.py:200-227`): When temperature exceeds 35, the player gets "The intense heat is draining your energy!" At below 5, "The cold is sapping your strength." Dead players (ghosts) get a separate message about no longer feeling physical sensations.

#### Air

Free-text field with several recognized values that generate specific description lines:

| Value     | Description |
|-----------|------------|
| `toxic`   | "The air is toxic and acrid." + warning "WARNING: The air is toxic! You're being damaged." |
| `stale`   | "The air feels stale and close." + "The air is stale and making you tired." |
| `humid`   | "The air is humid and heavy." |
| `smoky`   | "The air is thick with smoke." |
| `fragrant`| "A pleasant fragrance fills the air." |

#### Smell

Free-text, displayed if not `"neutral"`, `"fresh"`, or empty: `"A {smell} smell hangs in the air."`

Recognized foul smells (`engine/area_description.py:222-223`): `"mold"`, `"rot"`, `"rotting food"`, `"urine"` — these generate hygiene warnings.

#### Noise

Free-text, displayed as:

- `"loud"` or `"chaotic"`: `"The room is noisy with {noise} sounds."`
- Others: `"You hear {noise}."`
- `"quiet"`, `"silent"`, `""`: No description.

Noise also prevents restful sleep (`engine/area_description.py:219`): `"The noise is preventing restful sleep."`

### Other Area Properties

Rooms can have arbitrary additional properties stored in the `properties` dict. The serializer preserves these via `"properties": node.properties` (see `engine/serialization.py:68`). Common extras:

- **`floor`**: Integer floor number, used for organization. Defaults to 0.
- **`tags`**: Array of string tags for categorization.
- **`area`**: Area/region identifier (more on areas below).

## Area Descriptions

`RoomDescription` (`engine/area_description.py:6-312`) is the engine module responsible for building the full room text that a player sees when they `look`. The method `get_area_description()` (line 85-312) assembles:

1. **Base description** — from `player_manager.current_area.description`
2. **Light spill notification** — if the room is brighter due to spill from an adjacent room
3. **Item descriptions** — all visible items in the room (with `EDGE_IN` edges targeting this room, not hidden)
4. **Environmental summary** — temperature, air quality, smell, noise
5. **Players in room** — other characters present, their states, descriptions, and held items
6. **Warnings** — temperature extremes, toxic air, noise affecting sleep, foul smells
7. **Exit descriptions** — each visible door with its state, target room name, and environmental clues

### Light-Dependent Descriptions

When the player can't see properly, the description changes:
- **Pitch black** (`engine/area_description.py:98-99`): "It's pitch black. You can't see anything. You should find a way to illuminate this space."
- **Dim** (`engine/area_description.py:100-101`): "The light is dim — you can barely make out shapes. You need more light to see properly."

Ghosts and characters with the `dark_vision` trait skip this check entirely (`engine/lighting.py:67-80`).

### Exit Environment Clues

When a door is open and the player can see through it, the description includes environmental previews of the target room (`engine/area_description.py:260-298`):

```
To the north, the Kitchen is visible beyond (pitch dark, cold, dripping water audible).
```

This parses the target room's light level, noise, and temperature to build clue strings:
- `pitch dark` (light ≤ 20), `dimly lit` (≤ 40), `brightly lit` (≥ 90)
- `{noise} audible` (if noise is not quiet/silent)
- `bitterly cold` (< 5°C), `cold` (< 15°C), `warm` (> 28°C), `sweltering hot` (> 35°C)

### Items in Area Description

Items in a room are found by scanning `EDGE_IN` edges targeting the current room's node ID (`engine/area_description.py:129-138`):

```python
for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
    node = self.graph.get_node(edge.source)
    if node and node.type == "item" and not node.properties.get("hidden", False):
        item_desc = node.properties.get("description", "").strip()
        if item_desc:
            if not item_desc.endswith('.'):
                item_desc += '.'
            item_descs.append(item_desc)
```

Only non-hidden items with descriptions are listed. Hidden items (like secret keys) don't show up until discovered.

## Area Connections via Doors

Rooms are not directly connected to each other. The connection pattern is always:

```
room —[connection]→ door —[connection]→ room
```

Two `EDGE_CONNECTION` edges from each room to the door, plus two from the door to the opposite areas — for a total of 4 edges per bidirectional connection. This is set up in `MovementSystem.connect_areas()` (`engine/movement.py:45-73`):

```
room1 → door (direction: dir1)
door → room2 (direction: dir2)
room2 → door (direction: dir2)
door → room1 (direction: dir1)
```

The door node holds the state (open/closed/locked/blocked/broken/hidden), description, pass_message, cost, and trigger data.

This indirection through door nodes is what makes the system flexible — ways can have independent state, triggers, skill checks, auto-close behavior, and hidden visibility separate from the areas they connect.

For full details, see [Doors & Connections](Doors & Connections.md).

## The "Area" Concept

VirtualWorld has a nascent "area" concept that isn't fully wired into the engine. Here's what exists:

- **Area library files** live at `data/library/areas/*.json` — so far we have `world_template.json` and `mansion.json`. These are full room sets grouped by scenario.
- **Area library** at `data/library/areas/*.json` — the directory exists but is currently empty (see `AGENTS.md:99`).
- **Way library** at `data/library/ways/*.json` — also exists but empty (`AGENTS.md:100`).

The intended design (based on the library directory structure) seems to be:
- **Rooms** are individual spaces.
- **Areas** would group areas together into regions (e.g. "The Mansion Grounds" containing Garden, Graveyard, Crypt).
- **Ways** would be connections/paths between areas.

But currently, area grouping is not enforced by the engine. Rooms exist independently in the graph, and any room can connect to any other room regardless of "area" boundaries. The only grouping is logical — room names and door IDs can follow naming conventions.

For scenario files like `mansion.json`, areas are just organized under the `"areas"` key in the template file, and the legacy template loader (`engine/serialization.py:184-366`) processes them into graph nodes uniformly without area awareness.

## Area Library Files

Area library files in `data/library/areas/` use the same format as `world_template.json`. They contain:

1. **Players** — character definitions (personality, stats, vitals, skills, inventory, behaviors)
2. **Rooms** — room definitions with descriptions, environments, exits
3. **Active/starting state** — `current_area`, `active_player`, `game_time`, `time_ticks`
4. **Graph** — serialized graph nodes and edges

The library format is self-contained. Each file includes everything needed to reconstitute a full world state. The serialization module handles loading via `_load_from_template_format()` (single-player template, `serialization.py:184-366`) or `_build_graph_from_legacy()` (multi-player dict format, `serialization.py:367-506`).

When loading a template, areas are created first as bare graph nodes, then exits are processed to create door nodes and connection edges, then items are placed with `EDGE_IN` edges, and finally players are positioned. Triggers are created as `logic_trigger` nodes linked via `EDGE_TRIGGERS` edges.

### Area Registration

When importing from a template, areas get their description and environment set as node properties. The `Area` class in `room.py` is the legacy data object — it still wraps a `name`, `description`, `items`, `exits`, and `environment`, but modern code reads directly from the graph rather than reconstructing Area objects.

The `MovementSystem.add_area()` method (`engine/movement.py:23-35`) is rarely called directly now — areas are typically created when loading a save or template. The legacy `/api/build/room` endpoint (`routes/graph.py:163-187`) still exists for quick room creation via the UI.

## Edge Cases

- **Area with no description**: Falls back to `"You are in an empty void."` if `current_area` is None (`engine/area_description.py:87`).
- **Area deletion**: Protected — you can't delete a room with players inside it (`routes/graph.py:134-138`).
- **Duplicate room names**: Detected at graph insertion level — raises `ValueError` via `graph.py:58-59`.
- **Area name changes**: Renaming a room via `/api/graph/node/<id>/rename` updates all edge references (`routes/graph.py:96-124`).
- **Player state blocking movement**: Sleeping, unconscious, bound, and dead (without ghost mode) players cannot move (`engine/movement.py:97-101`).

## Related tasks

- [[dev_tasks/todo/gameplay/task-99-room-grids-and-movement|task-99: Area grids and movement]]
- [[dev_tasks/review/environment/task-5-heat_propagation|task-5: Heat propagation (temperature on areas)]]
- [[dev_tasks/review/environment/task-31-dynamic_room_descriptions|task-31: Dynamic room descriptions]]
- [[dev_tasks/review/environment/task-45-room_generator_room_context|task-45: Area generator room context]]
- [[dev_tasks/review/graph/task-46-room_tree_view|task-46: Area tree view]]
- [[dev_tasks/review/gameplay/task-48-time_advancement_per_turn|task-48: Time advancement per turn]]
- [[dev_tasks/review/environment/task-49-toggle_room_context_generation|task-49: Toggle room context generation]]
- [[dev_tasks/review/environment/task-43-relieve_adds_smell|task-43: Relieve adds smell]]
