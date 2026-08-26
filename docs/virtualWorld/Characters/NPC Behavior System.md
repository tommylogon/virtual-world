# NPC Behavior System

VirtualWorld supports two NPC paradigms: **LLM-driven agents** (no `simple_npc` flag, driven by the agent engine) and **simple NPCs** (`simple_npc = True`, driven by scripted behaviors). This document covers the simple NPC system.

## The `simple_npc` Flag

NPC type is determined by `simple_npc` on the `Player` object (`player.py:105-111`):

```python
self.simple_npc = False          # True = scripted, False = LLM-driven
self.npc_behavior = "wander"     # wander, flee, stationary
self.npc_action_interval = 3     # act every N ticks
self.npc_state = "idle"          # behavior state machine
self.state_enter_tick = 0        # tick when npc_state was entered
self.behaviors = []              # list of behavior definitions
```

### Differences Between NPC Types

| Aspect | Simple NPC (scripted) | LLM-Driven Agent |
|--------|----------------------|------------------|
| `simple_npc` | `True` | `False` |
| Intelligence | Scripted rules | LLM reasoning |
| Processing | `process_simple_npcs()` tick loop | Agent engine sends `/api/action` |
| Icon | 🐱 (cat emoji) | Standard player icon |
| Turn queue | Included (LLM step skipped; backend tick drives action) | Included |
| Behavior | `npc_behavior` + `behaviors[]` | Any in-character action |
| State | State machine (`npc_state`) | Free-form narrative |

## NPCBehaviorSystem (`engine/npc_behaviors.py`)

The `NPCBehaviorSystem` class manages all NPC behavior processing. It's initialized with references to the graph, player manager, trigger system, and game state (`npc_behaviors.py:15-19`).

### `process_simple_npcs()` (`npc_behaviors.py:27-129`)

Called from `tick_turn()` every tick (`tick_manager.py:317-318`). Processes all simple NPCs in order:

1. **Skip non-NPCs**: Characters where `simple_npc` is False
2. **Skip dead** characters
3. **Build context**: Current tick, NPC state, player room, player inventory
4. **Evaluate behaviors**: Sort by priority, filter by trigger type and interval
5. **Legacy fallback**: If no behavior matched, use `npc_behavior` (wander/flee/stationary)

#### Behavior Evaluation

Behaviors from the `behaviors[]` array are evaluated in priority order (highest first):

```python
sorted_behaviors = sorted(behaviors, key=lambda b: -b.get("priority", 0))
for behavior in sorted_behaviors:
    # Check trigger type match
    b_trigger = behavior.get("trigger")
    if b_trigger and b_trigger != trigger_type:
        continue
    # Check interval
    interval = behavior.get("interval", 1)
    if interval > 1 and self.gs.time_ticks % interval != 0:
        continue
    # Check conditions
    conditions = behavior.get("conditions", {})
    if conditions and not self.triggers._evaluate_conditions(conditions, context):
        continue
    # Execute actions
    actions = behavior.get("actions", [])
    if actions:
        outputs = self.triggers._execute_behavior_actions(pname, actions)
```

(`npc_behaviors.py:58-75`)

### Legacy NPC Behaviors

If no behavior definitions match (and `trigger_type == "on_tick"`), the legacy `npc_behavior` field is used:

#### wander (`npc_behaviors.py:85-102`)
1. Gets open exits from the current room
2. Picks a random direction
3. Temporarily switches `active_player` to the NPC
4. Calls `movement.move_to_room()` to move
5. Logs `"[NPC] <name> wanders <direction> to <room>."`

#### flee (`npc_behaviors.py:103-129`)
1. Checks if any non-NPC, non-dead player is in the same room
2. If a threat is nearby, picks a random open exit
3. Moves through that exit
4. Logs `"[NPC] <name> flees <direction> from a threat."`

#### stationary
Does nothing — NPC stays in place.

### Action Interval

Both the `npc_action_interval` field and per-behavior `interval` control how often NPCs act:

```python
interval = getattr(player, 'npc_action_interval', 3)
if self.gs.time_ticks % interval != 0:
    continue
```

(`npc_behaviors.py:79-80`)

Default interval: 3 ticks. An interval of 1 means act every tick.

## Behavior Definitions Format

Each behavior in the `behaviors[]` array is a dict:

```python
{
    "priority": 10,           # Higher = checked first
    "trigger": "on_tick",     # Trigger type (on_tick, on_combat, etc.)
    "interval": 3,            # Act every N ticks (1 = every tick)
    "conditions": {           # Conditions dict (evaluated by trigger system)
        "state_equals": "idle",
        "has_property": {"key": "low_hp", "value": True}
    },
    "actions": [              # List of action dicts
        {"type": "message", "params": {"text": "The guard scans the area."}},
        {"type": "move", "params": {"direction": "north"}}
    ]
}
```

### Visual authoring (task-226)

Behaviors are editable two ways: the character inspector's **Advanced → Behaviors** form, and
the **behavior graph editor** — the same canvas as the trigger editor (`static/js/shared/
trigger-graph.js`, behavior mode), opened via the 🧩 Graph buttons in the Behaviors form or
agent inspector. Nodes are behaviors/conditions/actions/states; **vertical position sets
priority** (top = highest priority, so you reorder by dragging), and Save round-trips to the
character's `behaviors[]` byte-identically.

### Trigger Types

Defined in the trigger system. Common NPC triggers include:
- `on_tick`: Fired every tick (interval-controlled)
- `on_combat`: Fired when combat occurs nearby

### Available Actions

Actions are executed by the trigger system's `_execute_behavior_actions()` (`trigger_system.py:438-632`). Standard action types:

| Action | Fields | Description |
|--------|--------|-------------|
| `message` | `text` | Output narration to log |
| `speak` | `text` | NPC speaks out loud (broadcasts to room) |
| `set_npc_state` | `state` | Change `npc_state` (e.g., `idle`, `scavenging`, `fleeing`, `eating`) |
| `damage` | `amount`, `target` | Deal damage to `player` or `self` |
| `heal` | `amount`, `stat`, `target` | Restore a vital (HP, Hunger, etc.) |
| `set_environment` | `stat`, `amount`, `area` | Change room environment |
| `spawn_item` | `item_id`, `display_name`, `description` | Create an item |
| `go` | `mode`, `area`/`room`, `areas` | Move one step via ways — see modes below |
| `teleport` | `area` | Instantly move to any area (no pathfinding) |

#### `go` movement modes (task-8)

| Mode | Fields | Behavior |
|------|--------|----------|
| `goto` (default) | `area` or `room` | BFS pathfind; one step via `move_to_area()` (doors, costs, locks) |
| `random` | — | Random open exit from current area |
| `patrol` | `areas` (comma-separated) | Cycle `patrol_route` on the NPC; one step toward current waypoint; advances index on arrival |

Patrol state persists on the player: `patrol_route[]`, `patrol_index`. Use `teleport` when you genuinely want to skip ways.

### Condition Types

Conditions are evaluated by `_evaluate_conditions()` (`trigger_system.py:337-431`). Supports logical operators and leaf types:

**Logical operators** (`conditions.operator`):
- `and` — all sub-conditions must pass
- `or` — any sub-condition passes
- `not` — negates sub-condition

**Leaf conditions** (`conditions.type`):

| Type | Fields | Evaluates |
|------|--------|-----------|
| `eq` | `target`, `value` | `context[target] == value` — checks context keys like `npc_state` |
| `has_item` | `item`, `target` | Checks if target has item in inventory |
| `in_area` | `area`, `target` | `context[npc_area] == area` |
| `random_chance` | `chance` (0.0–1.0) or `value` (0–100) | Probabilistic gate |
| `tick_since_state` | `min_ticks` | `(current_tick - state_enter_tick) >= min_ticks` |
| `proximity` | `max_areas` | Checks if player is within N areas of NPC (0 = same room) |

The context dict available to conditions:
```python
context = {
    "npc": player,                      # NPC Player object
    "npc_state": player.npc_state,       # e.g. "idle", "scavenging"
    "npc_area": player.current_area,     # Area name
    "state_enter_tick": ...,             # Tick when npc_state was entered
    "current_tick": ...,                 # Current game tick
    "player": player_obj,                # Active human player object
    "player_area": player_area,          # Active human player's area
}
```

### Trigger Types for Behaviors

Behaviors can be triggered by different events, passed via `process_simple_npcs(trigger_type)`:

| Trigger | When fired | Source |
|---------|-----------|--------|
| `on_tick` | Every tick (interval-controlled) | `tick_manager.py` |
| `on_player_enter_area` | When a player enters the NPC's area | `movement.py` |
| `on_player_leave_area` | When a player leaves the NPC's area | `movement.py` |
| `on_item_taken` | When an item is taken from the area | `item_actions.py` |
| `on_player_examine` | When a player examines something in the area | `narration.py` |

## npc_state State Machine

The `npc_state` field (`player.py:109`) tracks the NPC's current behavior state. It's a free-form string set by behaviors. The `state_enter_tick` (`player.py:110`) records when the current state was entered, enabling time-based state transitions.

No hardcoded state machine exists at the engine level — states and transitions are managed entirely through behavior definitions. Example state flow for the scavenging rat:

```
idle → fleeing (player close) → hiding (go to Kitchen) → scavenging (after 5 ticks) 
     → eating (find food, heal Hunger) → scavenging (finish eating) → explore Cellar/Kitchen
```

### Example: Scavenging Rat

The rat in the world template uses a full behavior state machine (`world_template.json`, player `rat`):

```
foraging ↔ eating (Hunger < 80) ↔ Kitchen/Cellar via go
idle → foraging (patrol)
fleeing → hiding → foraging (after ticks)
on_player_enter_area → whisker twitch + squeak
```

States: `idle`, `foraging`, `eating`, `fleeing`, `hiding`. Legacy `npc_behavior` is `stationary` so all movement comes from `behaviors[]` `go` actions (pathfinding via ways, one step per tick).

```json
{
  "trigger": "on_tick",
  "priority": 9,
  "interval": 2,
  "conditions": {
    "operator": "and",
    "conditions": [
      {"type": "proximity", "max_areas": 0},
      {"type": "random_chance", "chance": 0.55}
    ]
  },
  "actions": [
    {"type": "set_npc_state", "state": "fleeing"},
    {"type": "speak", "text": "Squeak!"},
    {"type": "message", "text": "The rat squeaks in alarm and darts for cover."}
  ]
}
```

## Legacy `npc_behavior` vs `behaviors[]`

**Prefer `behaviors[]` for anything that should feel alive.** The legacy string field (`wander`, `flee`, `stationary`) is a zero-config fallback when no behavior definition matches on `on_tick`:

| Legacy value | What it does | Status |
|--------------|--------------|--------|
| `wander` | Random open exit via `move_to_area()` | Works — good for placeholder NPCs |
| `flee` | Random exit when a non-NPC player shares the room | Works |
| `stationary` | Nothing | Works |
| `patrol`, `guard`, `follow`, `hunt`, `still` | Documented in places, **not implemented** in legacy fallback | Use `behaviors[]` instead |

Keep legacy wander/flee as a cheap default for animals and extras with no authored tree. Remove it from characters you care about (set `npc_behavior: "stationary"` and put all logic in `behaviors[]`).

**Internal wiring:** `process_simple_npcs()` must pass `game_state=self.gs` into `_evaluate_conditions()` and `_execute_behavior_actions()` — without it, scripted actions silently no-op.

## Hunt System

The `NPCBehaviorSystem` provides a BFS-based hunt system for aggressive NPCs:

### `hunt()` (`npc_behaviors.py:133-159`)

Agent-facing hunt command:
1. Finds the nearest living, non-slasher player via BFS through room connections
2. Returns the direction to move toward them
3. Returns flavor text ("sniffs the air", "growls in frustration")

### `slasher_hunt()` (`npc_behaviors.py:161-218`)

AI-driven hunt for slasher characters:
1. Finds nearest living player
2. If in same room: calls `_slasher_attack()`
3. Otherwise: BFS pathfinding, forces open closed doors
4. Moves the slasher toward the target

### Pathfinding

Both use `_get_path_to_room()` (`npc_behaviors.py:278-309`):
1. BFS from source room to target room
2. Traverses door nodes (open or closed)
3. Returns the first direction to take
4. Returns `None` if no path exists

`_get_nearest_player_to()` (`npc_behaviors.py:227-276`) finds the closest living player by BFS distance, excluding slashers from the target pool.

### Context Building

When processing behaviors, a context dict is built (`npc_behaviors.py:45-56`):

```python
context = {
    "npc": player,
    "npc_state": getattr(player, 'npc_state', 'idle'),
    "npc_area": player.current_area,
    "state_enter_tick": getattr(player, 'state_enter_tick', 0),
    "current_tick": self.gs.time_ticks,
    "player": player_obj,
    "player_area": player_area,
}
```

This context is passed to condition evaluation and can be extended with `extra_context`.

## Combat Reactions

`process_npcs_on_combat()` (`npc_behaviors.py:23-25`) is a stub called from `combat.py` when combat occurs. Currently empty (`pass`) — future implementation will allow NPCs to react to nearby combat.

## Creating Simple NPCs

### Via API

Create a simple NPC via `POST /api/players`:

```json
{
    "name": "Guard",
    "simple_npc": true,
    "npc_behavior": "stationary",
    "npc_action_interval": 2,
    "stats": {"STR": 12, "DEX": 10, "CON": 12, "INT": 8, "WIS": 10, "CHA": 8},
    "skills": {"Athletics": 3, "Perception": 2}
}
```

### Via Import

Character library files can set `simple_npc`:

```json
{
    "name": "Wandering Merchant",
    "simple_npc": true,
    "npc_behavior": "wander",
    "npc_action_interval": 5,
    "behaviors": [...],
    "inventory": ["goods", "coin_pouch"]
}
```

### Via Inspector UI

The Inspector UI has a behaviors panel for configuring NPC behaviors, states, and conditions visually.

## Edge Cases

### Dead NPCs

Simple NPCs in state `"dead"` are skipped entirely — they never act, wander, or flee (`npc_behaviors.py:35-36`).

### No Available Exits

If a wandering or fleeing NPC has no open exits from their current room, they stay in place. The code checks `if not open_exits: continue` (`npc_behaviors.py:91, 118`).

### Interval Desync

NPCs with different `npc_action_interval` values act on different ticks. An NPC with interval 3 acts on ticks 0, 3, 6, 9... This ensures NPCs don't all act simultaneously, spreading out the processing load.

### State Transitions

The `npc_state` field persists between ticks. Behaviors can change it via actions. The `state_enter_tick` records when the state was entered, allowing behaviors to check `tick_since_state_change > threshold`.

## LLM-Driven Agents vs. Scripted NPCs

This is a critical architectural distinction (`AGENTS.md:20`):

| Criterion | LLM Agent | Simple NPC |
|-----------|-----------|------------|
| `simple_npc` | `false` | `true` |
| Processing | Agent engine sends actions | `process_simple_npcs()` tick loop |
| Personality | Rich personality prompt, LLM interprets | No personality — scripted behavior |
| Flexibility | Can do anything in-character | Limited to defined behaviors |
| Cost | LLM API calls per action | Zero cost (local scripted) |
| Implementation | `agent-engine.js` (frontend) + `routes/action` | `engine/npc_behaviors.py` |
| Memory | Full memory system (`player.memories[]` — unified store) | None (unless manually scripted) |

LLM-driven agents are created the same way as simple NPCs (same `Player` class) but with `simple_npc = False`. The agent engine in `agent-engine.js` decides when they act by calling `/api/action` with the agent's name.

## Agent Memory System

Memory is the **unified `Player.memories[]` store** (task-178) — there is no separate
key-value `agent_memory.py` anymore. See [[AI & Narration/Memory System]].

- The agent writes **one memory per turn**: the LLM generates a subjective `memory` field in
  the react prompt (`{text, importance, tags}`), stored via `AgentMemory.storeMemory()` →
  POST `/api/players/<name>/memories/entry`.
- Plans live in the agent engine (`_plans[charName]` in `agent-engine.js`), not on the player.
- Reflection (`AgentMemory.reflect()`) summarizes high-importance memories into `reflection`
  memories every 5 turns.
- Spatial recall (KNOWN ROUTES) comes from `engine/spatial_memory.py` over `visited_areas`.

This is separate from the main `player.memories[]` list, which stores narrative memory entries for LLM context building.

## Related tasks

- [[dev_tasks/todo/characters/task-8-npc_behavior_movement|task-8: NPC behavior movement]]
- [[dev_tasks/todo/characters/task-92-needs_driven_autonomous_replanning|task-92: Needs-driven autonomous replanning]]
- [[dev_tasks/review/characters/task-38-npc_behavior_go_command|task-38: NPC behavior go command]]
- [[bug_8-max-steps-counts-characters-not-turns|bug-8: Max steps counts characters not turns]]
- [[dev_tasks/todo/characters/task-94-closeness_as_behavioral_gate|task-94: Closeness as behavioral gate]]
