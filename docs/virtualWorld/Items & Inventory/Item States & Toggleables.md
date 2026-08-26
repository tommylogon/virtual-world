# Item States & Toggleables

## Toggleable Items Overview

Toggleable items are items that can be switched between lit/unlit states, typically light sources like candles, flashlights, and lanterns. Managed by `engine/toggleable_items.py`.

### Toggleable Tag

An item is toggleable if it has `"toggleable"` in its `tags` array. Tags can be a list or comma-separated string:

```python
if isinstance(tags, str):
    tags = [t.strip() for t in tags.split(",")]
if "toggleable" not in tags:
    raise ValueError(f"The {item_name} can't be toggled on or off.")
```

### Activating (use command)

**Command**: `use <item_name>` — the `use_item()` handler in `item_actions.py:600-602` detects `"toggleable"` tag and redirects to `toggle_item_status()`.

**Backend**: `ToggleableItems.toggle_item_status()` (`engine/toggleable_items.py:15`)

Flow:
1. Find item node — line 19
2. Validate player — line 23
3. Check `"toggleable"` tag — lines 27-31
4. Read `current_state` from item node properties (default `"unlit"`) — line 31
5. If turning on, check `uses > 0`, decrement uses — lines 37-43
6. Flip `current_state` on item node — line 46
7. Build result message — verb depends on tags (lines 49-54):
   - `electric`/`synthetic` → "turn on / turn off"
   - Everything else → "light / extinguish"
8. Execute `on_toggle_on` or `on_toggle_off` triggers — lines 56-60
9. If uses hit 0, fire `on_depleted` trigger, flip state back to `"unlit"` — lines 63-67
10. Record turn event — line 69

### Verb Selection by Tag

The result message adapts to the item type:

| Tag | Turning on | Turning off |
|-----|-----------|-------------|
| `electric`, `synthetic` | "You turn the flashlight on." | "You turn the flashlight off." |
| (default: torch, candle, etc.) | "You light the torch." | "You extinguish the torch." |

Toggle triggers (`on_toggle_on`/`on_toggle_off`) should provide their own flavored messages. The base message is only shown as fallback.

### uses Depletion

When `uses > 0` and the item is toggled on, uses decrements by 1. When uses reaches 0:
- The `on_depleted` trigger fires
- `current_state` is set back to `"unlit"`
- The item cannot be toggled on again

## Light Contribution via Graph Scan

Light contribution uses **graph scanning** (`lighting.py:get_item_light_contribution()`), not per-player tracking. Items in the area or carried/equipped by characters are scanned for:

1. `"light_source"` tag — marks the item as light-emitting
2. `current_state == "lit"` — whether the item is currently on
3. `light_level` property — numeric (0–100) or string enum (`"dim"`, `"normal"`, etc.)

The sum of all matching items' `light_level` is added to the area's ambient light (capped at 100). This replaces the old per-player `item_statuses` + `item_active_effects` + `effect_target` system.

Benefits:
- **No per-player tracking**: all players in a room see the same light
- **No deltas on area transitions**: state lives on graph nodes
- **Free serialization**: graph nodes are serialized automatically
- **Drop/pickup works naturally**: removing an item from the area removes its light

### Drain Uses Per Tick When Active

In `tick_manager.py:283-308`, the system scans carried/equipped items with `current_state == "lit"`:

```python
for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
    for edge in self.graph.get_edges_for_target(player_node_id, edge_type):
        item_node = self.graph.get_node(edge.source)
        if item_node and item_node.type == "item" and item_node.properties.get("current_state") == "lit":
            lit_items.append(item_node)

for item_node in lit_items:
    tick_outputs = self.trigger_system._execute_triggers(item_node, "on_tick")
    if item_node.properties.get("uses", -1) == 0:
        item_node.properties["current_state"] = "unlit"
        dep_outputs = self.trigger_system._execute_triggers(item_node, "on_depleted")
```

Key behaviors:
- `on_tick` triggers (typically `adjust_uses`) handle fuel drain each tick
- When uses reach 0, `current_state` is set to `"unlit"` and `on_depleted` fires
- No more hardcoded decrement or `item_statuses` dict

### Light-Producing Items — Graph-Scan Pattern

Light-producing items are defined by tags and properties on the item node:

```json
{
  "name": "hand lamp",
  "uses": 60,
  "light_level": "normal",
  "current_state": "unlit",
  "tags": ["light_source", "toggleable", "oil_lamp"],
  "triggers": [
    {"trigger_type": "on_toggle_on", "effects": [{"type": "message", "params": {"message": "You light the lamp."}}]},
    {"trigger_type": "on_toggle_off", "effects": [{"type": "message", "params": {"message": "You extinguish the lamp."}}]},
    {"trigger_type": "on_tick", "effects": [{"type": "adjust_uses", "params": {"node_id": "self", "delta": -1}}]},
    {"trigger_type": "on_depleted", "effects": [{"type": "message", "params": {"message": "The lamp goes out."}}]}
  ]
}
```

Items with `light_level` but no `toggleable` tag are always-on stationary sources (e.g., a desk lamp that starts lit). Items with `toggleable` can be switched on/off by the player.

### Lighting and Actions

Low light blocks these actions:
- **Examine**: Blocked if light < 20 (`item_actions.py:41-43`)
- **Take**: Blocked if light < 20 (`item_actions.py:185-188`)
- **Use on target**: Blocked if light < 20 (`item_actions.py:628-632`)
- **Sanity**: Decays -1/tick when light < 20 (`tick_manager.py:213-215`)

## Progressive Item Status

Items can have multiple states via the `current_state` property. This is used by the trigger system for state transitions.

### State Transitions via Effects

The `handle_set_state` effect handler (`effects.py:194-239`) transitions a node's state:

```python
def handle_set_state(self, params, context, item_node=None, game_state=None):
    node_id = params.get("node_id", "")
    new_state = params.get("state", "open")
    target_node = self.graph.get_node(node_id)
    old_state = target_node.properties.get("current_state", "")
    target_node.properties["current_state"] = new_state
    # Fires on_state_exit and on_state_enter triggers recursively
```

### Multi-Use Items (Uses as State)

Items with `uses > 0` are effectively multi-state — each use decrements the counter until 0, then the item is consumed. The `handle_drain` effect (`effects.py:470-497`) reduces uses without consuming the item:
```python
def handle_drain(self, params, context, item_node=None, game_state=None):
    amount = int(params.get("amount", 1))
    uses = item_node.properties.get("uses", -1)
    if uses > 0:
        item_node.properties["uses"] = max(0, uses - amount)
```

The `handle_adjust_uses` effect (`effects.py:420-448`) can add or remove uses:
```python
def handle_adjust_uses(self, params, context, item_node=None, game_state=None):
    delta = int(params.get("delta", -1))
    target_node.properties["uses"] = max(0, current_uses + delta)
```

### Locked Items

Items with `current_state == "locked"` show a `locked_message` on examine (`item_actions.py:81-83`). Container items check for locked state before allowing contents to be accessed (`item_actions.py:263-264`).

## Trigger Types Related to Item States

| Trigger Type | When | Context |
|---|---|---|
| `on_toggle_on` | Item toggled on | `toggleable_items.py:75` |
| `on_toggle_off` | Item toggled off | `toggleable_items.py:77` |
| `on_depleted` | Item uses reach 0 | `tick_manager.py:304` |
| `on_tick` | Each tick while active | `tick_manager.py:293` |
| `on_state_exit` | State changes from X | `effects.py:221-228` |
| `on_state_enter` | State changes to Y | `effects.py:230-238` |
| `on_use` | Item used | `item_actions.py:553-556` |
| `on_examine` | Item examined | `item_actions.py:97-99` |
| `on_take` | Item taken | `item_actions.py:338` |
| `on_drop` | Item dropped | `item_actions.py:401` |

## Complete Toggleable Item Lifecycle (Graph-Scan Model)

1. **Item created** with `"light_source"` tag, `light_level` property, and `"toggleable"` tag (if player can turn it on/off)
2. **Player picks up** item — `EDGE_CARRYING` edge created. Light contribution follows the item's location
3. **Player toggles on** → `toggle_item_status()`:
   - Flips `current_state` to `"lit"` on the item node
   - Lighting scan picks it up automatically
   - Fires `on_toggle_on` triggers
4. **Each game tick** (`tick_turn()`):
   - Lighting scan re-evaluates all lit items in the area
   - `on_tick` triggers fire (typically `adjust_uses` for fuel drain)
   - When uses = 0: auto-flip to `"unlit"`, fire `on_depleted`
5. **Player moves to new room**:
   - Player's `EDGE_IN` edge changes. Next lighting scan sees items in new room instead of old
   - No explicit sync needed — state lives on graph nodes
6. **Player toggles off** → `toggle_item_status()`:
   - Flips `current_state` to `"unlit"`
   - Lighting scan no longer includes this item
   - Fires `on_toggle_off` triggers
7. **Player drops item** — `EDGE_CARRYING` edge removed, item reconnects to area via `EDGE_IN`. Lighting scan updates automatically

## Known Issues

- Some library items (candles, oil_lamp, phone) still have legacy `effect_target`/`effect_amount` fields alongside `light_level` — need conversion to pure graph-scan pattern
- `light_level` field should be present on all `light_source`-tagged items

## Entertainment Vital & Exploration

The Entertainment vital (`player.vitals["Entertainment"]`) decays naturally over time but can be boosted by exploration:

- **First-time area visit**: +15 Entertainment (×1.5 if `curious` trait, 0 if `homebody`)
- **Revisiting areas** (with `wanderlust` trait): +3 Entertainment
- **Met new characters**: small Entertainment boost (via `add_entertainment_gain`)
- Tracked per-character via `visited_areas: set[str]` and `discovered_items: set[str]`

### Trait-Driven Behavior Hints

Traits inject behavior-guiding text into LLM prompts via `buildTraitBehaviorContext()`:

| Trait | Prompt text |
|-------|-------------|
| `impatient` | "You are impatient — you act quickly without overthinking." |
| `patient` | "You are patient — you can tolerate waiting and rarely act impulsively." |
| `curious` | "You are curious — drawn to examine things and explore unfamiliar places." |
| `adventurous` | "You are adventurous — willing to take risks to seek new experiences." |
| `homebody` | "You are a homebody — you prefer familiar surroundings and are reluctant to leave." |
| `wanderlust` | "You have wanderlust — you feel restless staying in one place too long." |

### Low Entertainment Prompt Injection

When Entertainment drops below thresholds, the prompt includes drive text in the `=== YOUR STATE ===` section:

| Threshold | Prompt text |
|-----------|-------------|
| < 50 | "You're starting to get bored. Consider doing something new or going somewhere else." |
| < 25 | "You're bored. Routine feels stifling. You're drawn to try something different." |
| < 10 | "You're desperate for stimulation. Staying in place any longer is unbearable." |

## Related tasks

- [[dev_tasks/todo/items/task-102-progressive-item-status-multi-use|task-102: Progressive item status multi-use]]
- [[dev_tasks/review/items/task-20-item_locked_state|task-20: Item locked state]]
- [[dev_tasks/review/triggers/task-47-stateful_continuous_triggers|task-47: Stateful continuous triggers]]
- [[dev_tasks/review/characters/task-136-vital-entertainment-from-exploration|task-136: Entertainment vital from exploration]]
