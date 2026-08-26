# Doors & Connections

Doors are the glue that connects rooms into a traversable world. Every exit in VirtualWorld is a **door node** — there are no direct room-to-room connections. The pattern is always `room → door → room`, and this indirection is what makes the system powerful.

> **Character position at doors:** `open`, `close`, `go`, and `use [item] on [door]` walk the actor **AT** the way as part of the action. Witnesses see *"Jake at the north"* in room look and agent prompts. Transit areas use `transit`/`passage` tags for **back/forward** when AT an entry way. Full reference: [[Gameplay/Character Spatial Position]].

## Architecture

A door connection involves exactly **one door node** plus **four connection edges**:

```
       ┌─────────────────────────────┐
       │       room_living_room      │
       │  name: "Living Area"       │
       └──────────┬──────────────────┘
                  │ EDGE_CONNECTION (direction: "north")
                  ▼
       ┌─────────────────────────────┐
       │  door_Living Room_north     │
       │  type: "door"              │
       │  state: "closed"           │
       │  description: "A heavy oak │
       │    door leading to study." │
       │  cost: {energy: 1, time:1}│
       └──────────┬──────────────────┘
                  │ EDGE_CONNECTION (direction: "enter")
                  ▼
       ┌─────────────────────────────┐
       │       room_study           │
       │  name: "Study"            │
       └─────────────────────────────┘
```

And the reverse:
```
       room_study → door (direction: "south")
       door → room_living_room (direction: "south")
```

This setup is created by `MovementSystem.connect_rooms()` in `engine/movement.py:45-73`.

### Way Node Construction

From `engine/movement.py:48-61`:

```python
way_id = self.gs._way_node_id(f"{room1_name}_{dir1}")
door_node = Node(
    id=way_id,
    type="door",
    name=f"{room1_name}-{dir1}",
    properties={
        "current_state": state,     # "open", "closed", "locked", "blocked", "broken", "hidden"
        "description": desc,
        "cost": cost or {},
        "room_from": room1_name,
        "room_to": room2_name,
    }
)
self.graph.add_node(door_node)
```

The four edges are:
```python
# room1 → door (direction: dir1)
Edge(source=room1_id, target=way_id, type=EDGE_CONNECTION, properties={"direction": dir1})
# door → room2 (direction: dir2)
Edge(source=way_id, target=room2_id, type=EDGE_CONNECTION, properties={"direction": dir2})
# room2 → door (direction: dir2)
Edge(source=room2_id, target=way_id, type=EDGE_CONNECTION, properties={"direction": dir2})
# door → room1 (direction: dir1)
Edge(source=way_id, target=room1_id, type=EDGE_CONNECTION, properties={"direction": dir1})
```

## Node ID Conventions

Way node IDs follow `door_<RoomName>_<direction>` (note: RoomName preserves original casing, unlike room IDs which are lowercased). From `engine/node_ids.py:27-33`:

```python
@staticmethod
def way_node_id(area_name: str, direction: str) -> str:
    return f"door_{area_name.replace(' ', '_')}_{direction}"
```

So `way_node_id("Living Area", "north")` → `"door_Living Room_north"`. Notice the space in "Living Area" is replaced with underscore but the casing is preserved.

In practice, door IDs in the wild are somewhat inconsistent (normalized to lowercase sometimes, not others). Way lookup in `MovementSystem` uses fuzzy matching through the `name_matcher` system rather than exact ID matching.

Examples from `world_template.json`:
- `door_Kitchen_swinging` — swinging door between Kitchen and Living Area
- `door_Living Room_north` — ornate door from Living Area to Study
- `door_front` — front door (abbreviated ID, convention not strictly enforced)
- `door_cellar_trapdoor` — trapdoor between Kitchen and Cellar

## Way States

Each door node has a `current_state` property. The engine recognizes six states:

### open
The door is passable. Players can walk through freely. The room description shows the exit with a `[direction]` marker and a description of what's visible beyond.

From `engine/movement.py:167-172` — when a closed door is walked through, it auto-opens:

```python
door_node.properties["current_state"] = "open"
door_node.updated = time.time()
self.graph.nodes[way_id] = door_node
trigger_outputs = self.triggers._execute_triggers(door_node, "on_open")
```

### closed
The door is shut but not locked. Walking through it triggers an auto-open (with optional skill check — see "needs_open" below). Manually opening it calls `toggle_way(direction, "open")`.

From `engine/movement.py:130-171` — when moving through a closed door:

1. If `needs_open` is configured (skill check checkbox in the UI), it requires a skill roll (default Athletics, DC 10). On failure: "The {direction} requires effort to open. (Athletics DC 10: roll X)"
2. If `EDGE_TRIGGERS` edges with `trigger_type: "requires_open"` exist, conditions are evaluated. If any condition fails, the door stays closed with a custom fail message.
3. Otherwise, the door auto-opens and fires `on_open` triggers.

### locked
The door cannot be passed or opened without first unlocking it. Attempts to move through or toggle produce:

```
The {direction} is locked. You need to unlock it first.
```

Doors are unlocked via the trigger system — typically an `on_use_on` trigger on a key item that fires an `unlock_way` effect. Looking at `engine/effects.py` (referenced from `trigger_system.py`), the `unlock_way` effect changes the door's `current_state` from `"locked"` to `"closed"` — unlocking doesn't open it; the door becomes passable and auto-opens when walked through (`engine/movement.py:257`).

There's also a legacy `locked_with` key system (see `engine/serialization.py:364` — `_create_locked_with_unlocks()`). This was the old way of associating keys with locks before the trigger system took over.

### blocked
The door is impassable due to an obstacle. Movement and toggle both fail:

```
The {direction} is blocked. There's no way through.
```

### broken
The door is physically broken. Toggle fails with:

```
The {direction} is broken.
```

### hidden
The door is invisible to normal perception. It does not appear in room exit descriptions unless:
- The player is a "slasher" type (has `is_slasher` trait) — see `engine/area_description.py:54-56`
- The player has discovered it via `discovered_exits` — see `player.py:97`: `self.discovered_exits = set()`

Hidden doors become visible through the `fumble_around()` action (Perception DC 12, per `AGENTS.md:167`). Once discovered, the exit key `(area_name, direction)` is added to the player's `discovered_exits` set.

Hidden doors in data files use `"state": "hidden"` or `"hidden": true` on the exit data. The serialization layer converts this during template loading (`engine/serialization.py:242`):

```python
"current_state": "hidden" if exit_data.get("hidden", False) else exit_data.get("state", "open"),
```

In the graph visualization (`static/js/graph/network-manager.js:124-125`), hidden doors render with a muted gray border: `{background: '#1a1a2a', border: '#6e7681'}`.

## Core Way Operations

### toggle_way(direction, action)

Defined in `engine/movement.py:244-315`. Opens or closes a door by direction name from the current room.

Flow:
1. Validates player isn't sleeping/unconscious/bound. Dead players need ghost mode + Perception DC 15 skill check.
2. Fuzzy-matches the direction string to actual exit directions using `name_matcher._match_exit_direction()`.
3. Checks door state — locked/blocked/broken all raise ValueError.
4. If the door is already in the target state, returns `"The {direction} is already {state}."`
5. Updates `current_state` on the door node.
6. Applies action cost (energy/time) if player is alive.
7. Fires `on_open` or `on_close` triggers.
8. Records a turn event.
9. If the new state is `"open"` and the edge has `visible_in_direction`, appends that text.

Ghost interaction check (`engine/movement.py:253-256`):
```python
success, _, msg = self.gs.skill_check("Perception", 15)
if not success:
    return f"Your ghostly hands pass right through the {direction}. You can't grasp it."
```

### toggle_way_by_id(way_id, action)

Defined in `engine/movement.py:317-359`. Same as `toggle_way` but takes a door's graph node ID instead of a direction name. Does a case-insensitive search across all door nodes to find the right one.

### _set_exit_state(area_name, direction, new_state)

Defined in `engine/movement.py:75-87`. Low-level state update — finds the door node at the given direction from the given room and sets `current_state` directly. Used by the trigger system and admin operations.

### move_to_room(direction)

Defined in `engine/movement.py:91-240`. The main movement function. Flow:

1. Validates player state (can't move while sleeping/unconscious/bound).
2. Fuzzy-matches the direction string.
3. Checks passage gates (`requires` + `max_size` — crawl/climb/jump verbs, auto-crawl, size block).
4. For climb/jump ways: rolls an Athletics check; failure fires `on_fail_climb`/`on_fail_jump`.
5. Checks door state — locked/blocked fail.
6. For closed doors: handles `needs_open` skill check, `requires_open` trigger conditions, or auto-opens.
7. Finds the target room on the other side of the door.
8. Triggers NPC `on_player_leave_room` behaviors in the old room.
9. Moves the player via `name_matcher._set_player_room()`.
10. Syncs toggleable item effects to the new room.
11. Records turn events for leaving and entering.
12. Triggers NPC `on_player_enter_room` behaviors in the new room.
13. Applies movement cost (energy/time; crawl/climb scale time).
14. Fires `on_enter` triggers on the door (used for auto-close, traps, etc.).
15. If `auto_close` is enabled on the door, closes it behind the player and fires `on_close` triggers.

## Way Properties

### current_state
String: `"open"`, `"closed"`, `"locked"`, `"blocked"`, `"broken"`, `"hidden"`. Controls whether the door is visible and passable.

### description
Free-text shown in the room's exit list. Displayed as `"[{direction}] {description} It is currently closed."` when the door is not open — the door's mechanical state (`locked`/`blocked`/`broken`) is only revealed by examining the door itself, so the glance listing never leaks it.

### pass_message
Replaces the default movement text (`"You head through the {direction}."`) with custom flavor text. From `engine/movement.py:237-239`:

```python
pass_msg = door_node.properties.get("pass_message", "")
target_display = target_area_node.properties.get("display_name") or target_area_node.name
arrival_suffix = f" — you're in {target_display}."
if pass_msg:
    return pass_msg + arrival_suffix
return f"You head through the {direction}." + arrival_suffix
```

The destination area name is always appended (`" — you're in {Name}."`) so agents and players know where they ended up.

### cost
Dict of resource costs for moving through the door, e.g. `{"energy": 1, "time": 1}`. Applied to the player via `self.gs.apply_action("move", exit_cost, player=self.gs.player)` at `engine/movement.py:221-223`.

### room_from / room_to
Informational strings identifying which two rooms this door connects. Used by the serialization and UI for display purposes. Not relied on for graph traversal (that uses the edges).

### auto_close
Boolean. If true, the door closes automatically after the player passes through. From `engine/movement.py:229-235`:

```python
if door_node.properties.get("auto_close", False):
    door_node.properties["current_state"] = "closed"
    ...
    close_outputs = self.triggers._execute_triggers(door_node, "on_close")
```

### needs_open
Used for skill-gated doors (checkbox in the UI). Structure:

```python
{
    "enabled": True,
    "skill": "Athletics",  # default
    "dc": 15               # default
}
```

When set, the player must pass a skill check to open the door. Failure produces: `"The {direction} requires effort to open. ({skill} DC {dc}: roll {total})"`. On success, the door auto-opens.

From `engine/movement.py:132-146`:
```python
needs_open = door_node.properties.get("needs_open", {})
if needs_open.get("enabled", False):
    skill = needs_open.get("skill", "Athletics")
    dc = int(needs_open.get("dc", 10))
    success, total, msg = self.gs.skill_check(skill, dc)
    if not success:
        raise ValueError(f"The {direction} requires effort to open. ({skill} DC {dc}: roll {total})")
```

### requires (passage mode) — task-187
String: `""` (walk through), `"crawl"`, `"climb"`, or `"jump"`. Gates which movement verb passes the way. Checked in `move_to_area` (`engine/movement.py:151-156`):

- `requires: crawl` — a crawl-only tunnel. Plain `go` **auto-converts to a crawl** (you can't walk it).
- `requires: climb` — only `climb <dir>` passes; `go` raises `"You need to climb through the {direction}."`
- `requires: jump` — only `jump <dir>` passes; `go` raises `"You need to jump through the {direction}."`

Climb/jump ways roll an **Athletics check** (default DC 12, override with a `climb_dc` / `jump_dc` property). On failure the way's `on_fail_climb` / `on_fail_jump` trigger fires if present (damage, narrative, etc.); otherwise the move just doesn't happen with a generic message. Failure is fully trigger-driven — no hardcoded consequences.

### max_size (size gate) — task-187
String: `""` (no limit), `"tiny"`, `"small"`, `"normal"`, `"huge"`, `"giant"`, `"titanic"`. The largest character size that passes the way. Checked in `move_to_area` (`engine/movement.py:158-169`) against the player's size trait tier (`engine/size.py`):

| Condition | Result |
|-----------|--------|
| size ≤ `max_size` | Normal move |
| size = `max_size` + 1 tier (e.g. `normal` in a `small` tunnel) | **Auto-crawl**: `go` converts to a crawl — "You drop to your hands and knees and crawl through..." |
| size ≥ `max_size` + 2 tiers | **Blocked**: `"You don't fit through the {direction}."` |

Character size comes from the mutually-exclusive `size_*` traits (`size_tiny` … `size_titanic`, default `normal` — see [[Characters/Traits System]]). Crawl/climb/jump do **not** scale the way's cost in v1 — the `time` field is a duration hint for the future stateful-action system (task-131); the clock advances once per turn for everyone (`tick_turn` → `advance_clock(1)`), never per action.

### visible_in_direction
Stored on the *edge* from room to door, not on the door node itself. When the door is open (or if `see_through` is set — see below), this text is shown as the "what you see beyond" description. For example:

```
To the north, the Kitchen is visible beyond (pitch dark, cold, dripping water audible).
```

Or if `visible_in_direction` is set directly, it uses that text verbatim:

```
[north] The kitchen, with a checkered tablecloth on the table and dried herbs hanging from the ceiling.
```

See `engine/area_description.py:260-265` for the fallback logic.

### see_through
Boolean. When true, the door acts as a window — `visible_in_direction` text is shown even when the door is closed. Light also spills through the door regardless of state (see `engine/lighting.py:54`).

Used for windows, glass doors, portcullises, fence gates, or any barrier you can see/look through but can't (or haven't yet) walked through.

Typical setup:

```json
{
  "current_state": "closed",
  "description": "A large window overlooking the moonlit garden.",
  "see_through": true,
  "cost": {"energy": 3, "time": 2}
}
```

With `visible_in_direction` on the room→door edge:

```json
{
  "direction": "north",
  "visible_in_direction": "Through the window you can see a moonlit garden beyond."
}
```

The exit renders as:

```
[north] Through the window you can see a moonlit garden beyond.
```

The auto-generated peek-through (light/noise/temperature clues from the target room) is NOT shown for see_through doors — use `visible_in_direction` to write custom text, or omit it for no peek-through at all.

### tags
Array of string tags on the door node, e.g. `["secret", "magical"]`. Used for categorization and potential trigger targeting.

## Hidden Doors

Hidden doors are a first-class state, not just a flag. A door with `current_state: "hidden"` is invisible in room descriptions. The visibility logic is in `engine/area_description.py:52-62`:

```python
if door_node.properties.get("current_state") == "hidden":
    p = self.player_manager.players.get(self.player_manager.active_player)
    if self.player_manager.active_player and self.player_manager.is_slasher(self.player_manager.active_player):
        pass  # slashers can see hidden doors
    elif p and hasattr(p, 'discovered_exits'):
        exit_key = (area_name, direction)
        if exit_key not in p.discovered_exits:
            continue  # hidden unless discovered
    else:
        continue  # hidden
```

The same logic repeats in the exit description loop at line 242-251.

### Discovering Hidden Doors

The `fumble_around()` action triggers a Perception check (DC 12). On success, the exit key is added to `player.discovered_exits` and the door becomes visible. This uses the `discovered_exits` set on the Player object (`player.py:97`).

## Windows

Windows are doors with `see_through: true`. They behave as a visual portal between rooms — you can see through them (and light passes through), but traversal requires opening them (or a skill check / `requires_open` trigger).

### Window Properties

| Property | Required | Effect |
|----------|----------|--------|
| `current_state` | yes | Usually `"closed"` — windows don't auto-open on walk attempt |
| `see_through` | yes | `true` — enables peek-through and light spill regardless of state |
| `description` | yes | Shown in room exits (text only — it's replaced by `visible_in_direction` if set) |
| `cost` | no | Energy/time cost for climbing through |
| `visible_in_direction` | on edge | Custom "what you see" text shown always (set on the room→door edge, not the door node itself) |
| `auto_close` | no | Typically false for windows |

### Window Patterns

**1. Decorative window** (no traversal possible):
```json
{
  "current_state": "closed",
  "description": "A tall stained-glass window depicting a serpent eating its own tail.",
  "see_through": true
}
```
Edge has no `visible_in_direction` — the door's `description` shows in the exit list: `[east] A tall stained-glass window... It is currently closed.`

**2. See-through window** (casement you can open):
```json
{
  "current_state": "closed",
  "description": "A casement window looking out over the alley.",
  "see_through": true,
  "cost": {"energy": 2, "time": 1}
}
```
With `visible_in_direction` on the edge: `[east] The alley below, dark and narrow.`

**3. Window with skill-gated traversal** (requires climbing out):
```json
{
  "current_state": "closed",
  "description": "A small window set high in the wall.",
  "see_through": true,
  "cost": {"energy": 3, "time": 2}
}
```
With `requires_open` trigger conditions (Athletics DC 12 to climb out). See "requires_open Triggers" section.

**4. Window with light spill** — light from a lit room spills into the adjacent room through the window. No additional config needed — `see_through` is all that's required. See `engine/lighting.py:54`.

### Movement Through Windows

Windows are closed doors — walking into them triggers the normal closed-door flow:
1. If `needs_open` is set: skill check required
2. If `requires_open` triggers exist: conditions evaluated
3. Otherwise: door auto-opens (same as any closed door)

To prevent accidental auto-open (you want the player to explicitly open the window), add a `requires_open` trigger with a condition that always fails, e.g.:

```json
{
  "trigger_type": "requires_open",
  "conditions": [{"type": "has_trait", "trait": "can_phase_through_walls"}],
  "effect_params": {"fail_message": "You'd need to open the window first."}
}
```

This is a gating trick — the condition targets a trait no one has, so the door stays closed until toggled via `open` / `toggle`.

### Light Spill

Windows allow light to pass between rooms regardless of state. This is handled in `engine/lighting.py:54`:

```python
if door and door.type == "door" and (door.properties.get("current_state") == "open" or door.properties.get("see_through")):
```

A brightly lit room with a window into a dark room provides `max(own_light, spill_light * 0.5)` ambient light in the dark room.

### Graph Visualization

In the vis.js graph UI, `see_through` doors could be distinguished from regular doors by a glass-like visual treatment (transparent/translucent node fill). This is not yet implemented — currently windows render the same as any other door by `current_state`.

Hidden doors can also be revealed via triggers — for example, the "Loose Floorboard" examinable item in the template sets a hidden door to `open` via an `on_examine → set_state` trigger:

```json
// From world_template.json logic_trigger node
{
    "trigger_type": "on_examine",
    "effect_type": "set_state",
    "effect_params": {
        "message": "When you step on the board a click is heard and a hidden door opens up",
        "node_id": "door_Upstairs Hallway_",
        "state": "open"
    }
}
```

## Directional vs Named Exits

Doors can use either:
- **Cardinal directions**: `"north"`, `"south"`, `"east"`, `"west"` — these can be matched against arrow key presses and short direction names.
- **Named exits**: `"ornate door"`, `"front door"`, `"swinging door"`, `"ladder"`, `"stairs"`, `"trapdoor"` — any arbitrary string.

The `name_matcher._match_exit_direction()` system handles matching against both types, in tiers: exact label → word-boundary substring → way node name / target area name / cardinal → way description words → fuzzy difflib. Player can type `"north"`, `"n"`, `"front door"`, `"front"`, `"door"`, `"the circular door with the keycard slot"`, or the room name it leads to and get reasonable matches. The mechanical state (`locked`/`blocked`) is never matched as a target.

The edge property `"cardinal"` can be set to mark an exit as cardinal for movement shorthand. The RoomDescription system checks for this at `engine/area_description.py:79-80`:

```python
if "cardinal" in edge.properties:
    exit_data["cardinal"] = edge.properties["cardinal"]
```

## Edge Cost for Movement

Each door can have a `cost` dict specifying the resource drain for traversing it:

```python
{"energy": 1, "time": 1}
```

Applied at `engine/movement.py:221-223`:

```python
if self.gs.player.state != "dead":
    exit_cost = door_node.properties.get("cost", {})
    self.gs.apply_action("move", exit_cost, player=self.gs.player)
```

Ghosts bypass the cost entirely (they're ethereal). The cost can include any vital stat, not just energy/time — though energy and time are the standard ones.

### Traversal Distance via Midpoint Areas (design pattern)

For *distance*, don't track "how far along a way" a character is — chain midpoint areas instead. Every `go` through a way costs one action, so a passage made of N segments naturally takes N turns with zero extra engine logic:

```
Tunnel Entrance  →  Inside Tunnel (claustrophobic, size: small)  →  Tunnel Exit
First Floor  →  Stairs Up  →  Landing (Floor 2)  →  Stairs Up  →  Second Floor
```

This composes with way `cost` above: midpoint areas model *distance*, the `cost` dict on a way models *effort* (e.g. a crawl-only squeeze can drain energy/fatigue on top of the turns).

What each midpoint gets for free:

- Its own `description` / `environment` (light, temperature, air, smell, noise) — "inside the tunnel" is a real place.
- Size/feeling tags (`size: small`, `claustrophobic`) for conditions and trait checks.
- Light spill from adjacent areas propagates through open ways (`GraphNetwork._computeAmbientLight`), so midpoints inherit glow from both ends.
- Back-link directions are auto-hidden by `build_exits_for_area`, so a midpoint naturally lists both directions without hand-written reverse exits.
- Cardinal layout / map view places the chain spatially, so staircases render as real staircases on the graph.

Gotchas:

- NPC wander behavior picks open exits at random, so NPCs will occasionally mill around inside long passages — usually just realistic, but if it bothers you, tag midpoints `is_transit` and have wander skip transit areas (small engine tweak, not yet implemented).
- Every midpoint is a separate discovery point for the hidden-exit system — usually a feature (you discover the tunnel interior separately), sometimes a quirk.
- It costs a way edge pair per segment, so keep midpoints meaningful (landings, bends, rooms-within-tunnels) rather than every 2 meters.

## Unlock via Triggers

The modern unlock system uses `unlock_way` effects triggered from key items. The trigger system evaluates conditions and executes effects:

From `trigger_system.py`, the `unlock_way` effect type (line 60 in the `EFFECT_TYPES` list) changes a door's `current_state` from `"locked"` to `"closed"` (handled in `engine/effects.py:550`).

A typical key item has:
- `actions`: `["examine", "take", "use"]`
- `on_use_on` trigger targeting the door
- Effect: `unlock_way` with target node ID

The trigger system's `_execute_triggers()` method (`trigger_system.py:760-1044`) handles filtering by trigger type, evaluating conditions, and running effects. For `on_use_on` triggers, it checks `target_name` matching:

```python
if trigger_types_on_edge == "on_use_on" and target_name:
    required_target = trigger_edge.properties.get("target_name", "").lower()
    if required_target and target_name.lower() != required_target:
        continue
```

There's also a legacy `locked_with` system from before the trigger-based unlock existed. The `_create_locked_with_unlocks()` method in `engine/legacy_compat.py` (referenced from `serialization.py:364`) creates unlock edges from items to doors based on old-format data. This is still called during template loading for backward compat.

## Reconnecting Doors

Doors can be re-wired to connect different rooms via `/api/graph/door/reconnect` (`routes/graph.py:386-432`):

```python
way_id = data.get('way_id')
new_room_a = data.get('room_a')
new_room_b = data.get('room_b')
```

This removes all connection edges for the door, adds new ones to the specified rooms, and updates `room_from`/`room_to` display properties. Pretty clean — doors are just data, so re-routing is trivial.

## Way Triggers

Doors support the full trigger system. Common trigger types on doors:

| Trigger | When Fired | Use Case |
|---------|-----------|----------|
| `on_open` | Way state changes to open | Logging, ambient effects, revealing secrets |
| `on_close` | Way state changes to closed | Traps, sealing passages |
| `on_enter` | Player walks through the door | Auto-close, damage, teleport |
| `on_fail_climb` | A `requires: climb` way's Athletics check fails | Falling damage, losing grip, narrative |
| `on_fail_jump` | A `requires: jump` way's Athletics check fails | Slipping, falling into the gap |

Triggers are created as `logic_trigger` nodes linked to the door via `EDGE_TRIGGERS` edges. They're set up during `connect_rooms()` or via the `/api/build/connect` endpoint (`routes/graph.py:366-382`):

```python
trigger_node_id = f"trigger_{way_id}_{trigger_type}_{i}"
trigger_node = Node(
    id=trigger_node_id,
    type='logic_trigger',
    name=f"{way_id}:{trigger_type}",
    properties=tdata
)
app.world.graph.add_node(trigger_node)
app.world.graph.add_edge(Edge(
    source=way_id, target=trigger_node_id,
    type='triggers', properties=tdata
))
```

### requires_open Triggers

A special trigger type that gates movement through a closed door. Defined in `engine/movement.py:148-165`:

```python
req_open_triggers = [
    e for e in self.graph.get_edges_for_source(way_id, EDGE_TRIGGERS)
    if e.properties.get("trigger_type") == "requires_open"
]
```

These are checked when trying to walk through a closed door that doesn't have a `needs_open` skill check. If conditions fail, the player gets a custom failure message. This allows barricaded doors, magical seals, or any conditional block on passage.

## Graph Visualization

In the vis.js graph UI (`static/js/graph/network-manager.js:116-131`), doors are rendered as triangle nodes colored by state:

| State  | Border Color | Background |
|--------|-------------|------------|
| open   | `#3fb950` (green) | `#1a3a2a` |
| closed | `#e3b341` (amber) | `#2d3a1a` |
| locked | `#f85149` (red) | `#3a1a1a` |
| hidden | `#6e7681` (gray) | `#1a1a2a` |
| blocked| `#f0883e` (orange)| `#3a2a1a` |
| broken | `#f85149` (red) | `#3a1a1a` |

Connection edges are colored `#4ec9b0` (teal) by default. Trigger edges (`EDGE_TRIGGERS`) are skipped in the graph visualization entirely — they're managed via the Inspector panel only.

## Way Inspector

The frontend has a dedicated way inspector (`static/js/inspector/way-view.js`) for editing way properties. Right-clicking a way node in the graph context menu offers: Inspect, Edit Way, Add Trigger Edge, Delete Way, Duplicate. In addition to state, description, pass message, and auto-close, it exposes the **"Passage requires"** dropdown (`crawl` / `climb` / `jump` / none) and the **"Max size through"** dropdown (tiny … titanic / any) — the way properties documented above (task-187). The AI Improve flow also knows about these fields.

## Edge Cases

- **Way leads nowhere**: If the door's target edge doesn't point to a valid room, movement raises `ValueError: "The {direction} leads nowhere."` (`engine/movement.py:179-180`).
- **Same door from both sides**: When room1 → door (dir1) and room2 → door (dir2), both rooms see the same door node but with different direction labels. The door's state is shared.
- **Multiple doors on same direction**: Not supported per-room-direction pair — `connect_rooms` creates unique door IDs, but direction matching finds the first match.
- **Way cost is per-traversal**: Applied every time the player moves through the door. Ghosts skip cost.
- **Fuzzy direction matching**: Uses `name_matcher._match_exit_direction()` to handle typos, abbreviations, and partial names.

## Related tasks

- [[dev_tasks/review/triggers/task-15-door_trigger_events|task-15: Way trigger events]]
- [[dev_tasks/review/items/task-20-item_locked_state|task-20: Item locked state]]
- [[dev_tasks/review/items/task-23-remove_locked_with|task-23: Remove locked_with]]
- [[dev_tasks/review/triggers/task-30-door_requires_open_trigger|task-30: Way requires_open trigger]]
- [[dev_tasks/review/items/task-97-consolidate_locked_into_current_state|task-97: Consolidate locked into current_state]]
- [[dev_tasks/review/gameplay/task-187-character-size-passage-movement|task-187: Character size + passage movement]]
- [[dev_tasks/todo/environment/task-230-outdoor-lighting-time-of-day|task-230: Time-of-Day Outdoor Lighting]]
