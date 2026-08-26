# Triggers & Effects

## Overview

The Trigger System is the primary mechanism for creating interactive, reactive objects in VirtualWorld. It connects items (and other nodes) to reusable `logic_trigger` nodes via `EDGE_TRIGGERS` edges, which define what happens when a player interacts with the item in a specific way.

The system lives in `engine/trigger_system.py` (class `TriggerSystem`, ~1044 lines). Effects are dispatched to `engine/effects.py` (class `Effects`, ~724 lines). Conditions can gate whether a trigger fires.

## Graph Structure

### Edge Type

Trigger connections use `EDGE_TRIGGERS = "triggers"` (defined in `graph.py:174`). These are directed edges from a source node (typically an item) to a target `logic_trigger` node:

```
item_rusty_key --[triggers]--> trigger_rusty_key_on_use_1234
```

### Trigger Node ID Convention

Trigger nodes follow the pattern:

```
trigger_<parent_name>_<trigger_type>_<timestamp>
```

Examples from `AGENTS.md`:
- `trigger_rusty_key_on_use_1234`

This convention is documented in `AGENTS.md` but not enforced in code—any node of type `logic_trigger` works.

### Hidden from Visualization

Trigger edges and `logic_trigger` nodes are **hidden from graph visualization** (managed exclusively via the Inspector UI). This is documented in `AGENTS.md` and handled by the frontend graph display code.

## Trigger Types

Defined in `TRIGGER_TYPES` at `engine/trigger_system.py:16-43`:

| Trigger Type | Fires When... | Source |
|---|---|---|
| `on_take` | Item is picked up | `item_actions.py` |
| `on_drop` | Item is dropped | `item_actions.py` |
| `on_examine` | Item is examined | `item_actions.py` |
| `on_inspect` | Item is inspected (right-click) | Inspector UI |
| `on_use` | Item is used (generic) | `item_actions.py` |
| `on_use_on` | Item is used on a specific target | `item_actions.py` |
| `on_look` | Area is looked at (with item present) | `area_description.py` |
| `on_tick` | Tick manager processes active items | `tick_manager.py:293` |
| `on_eat` | Item is eaten | `item_actions.py` |
| `on_drink` | Item is drunk | `item_actions.py` |
| `on_read` | Item is read | `item_actions.py` |
| `on_light` | Item is lit (torch/candle) | — |
| `on_activate` | Item is activated | — |
| `on_equip` | Item is equipped | `equipment.py` |
| `on_unequip` | Item is unequipped | `equipment.py` |
| `on_throw` | Item is thrown | — |
| `on_break` | Item is broken | — |
| `on_depleted` | Item uses reach 0 | `tick_manager.py:304` |
| `on_toggle_on` | Item is toggled on | `toggleable_items.py` |
| `on_toggle_off` | Item is toggled off | `toggleable_items.py` |
| `on_open` | Item is opened | `item_actions.py` |
| `on_close` | Item is closed | `item_actions.py` |
| `on_state_enter` | Node enters a specific state | `effects.py:handle_set_state` |
| `on_state_exit` | Node exits a specific state | `effects.py:handle_set_state` |
| `on_auto_open` | Way auto-opens | — |
| `on_enter` | Player enters a room | — |
| `on_delayed` | A `schedule_trigger` effect's delay elapses | `tick_manager.py` (delayed event queue) |

## Effect Types

Defined in `EFFECT_TYPES` in `engine/trigger_system.py`; the editor dropdowns mirror the same
list from `static/js/shared/trigger-types.js` (single source of truth for the UI).

| Effect Type | What It Does | Handler in `effects.py` |
|---|---|---|
| `message` | Outputs narrative text to the log; an empty message produces no output (no generic "Something happens." placeholder) | `handle_message` |
| `save` | **Save gate** for fear/hazard triggers: `{"stat": "WIS", "dc": 12, "on_fail": [...effects], "on_success": [...]}` — applies `frightened` with this node as `source`/`source_type` on fail; drives trait `save_on` events (task-159/task-269) | `handle_save` |
| `damage` | Deals damage to self or other target. Optional `save` param makes it resistible: `{"save": {"stat": "DEX", "dc": 12, "on_success": "half"\|"none"}}` — on a successful save the damage is halved (default) or avoided entirely (task-159) | `handle_damage` |
| `heal` | Restores a vital stat (HP by default) | `handle_heal` |
| `spawn_item` | Creates an item node in the current room; optional `current_state` param overrides the library item's spawn state (e.g. spawn a pre-lit ember) | `handle_spawn_item` |
| `spawn_character` | Spawns a character from a library entry into a target area (ambushes, arrivals) | `handle_spawn_character` |
| `add_tag` / `remove_tag` | Adds/removes a tag on a target node (pairs with `target_tag`-based effects) | handlers |
| `set_parameter` / `adjust_parameter` | Set or increment a named parameter on a node (`params` system, task-203) | parameter handlers |
| `surface_memory` | Forces memories matching a tag/keyword back into a character's recall block | memory handler |
| `suppress_memory` | Blocks recall of matching memories (curses, trauma) | memory handler |
| `unblock_memory` | Lifts a `suppress_memory` block | memory handler |
| `give_item` | Hydrates a library item and places it directly into a character's inventory (`item_id`, `target`: self/target/name, optional `message`) — e.g. a failed Medicine check on a corpse puts the hidden disease carrier on you | `handle_give_item` |
| `remove_item` | Removes an item node from the graph entirely | `handle_remove_item` |
| `set_state` | Changes a node's `current_state` property; fires `on_state_exit`/`on_state_enter` | `handle_set_state` |
| `set_environment` | Overrides room environment properties (light, temperature, air, smell, noise) | `handle_set_environment` |
| `teleport` | Moves the active player to a different room | `handle_teleport` |
| `rename` | Renames a node | — |
| `unlock_way` | Sets a door node to `closed` state (unlocking doesn't open it — it becomes passable and auto-opens on walk-through). `way_id` accepts a way id, or `"target"`/blank to unlock the **used-on door** of an `on_use_on` trigger (for keycard designs) | `handle_unlock_way` |
| `drain` | Reduces an item's remaining uses | `handle_drain` |
| `adjust_vital` | Incrementally adjusts HP/Energy/Sanity on self or target | `handle_adjust_vital` |
| `adjust_environment` | Incrementally adjusts temperature/light/air/smell/noise | `handle_adjust_environment` |
| `set_hidden` | Toggles the hidden property on a node | `handle_set_hidden` |
| `adjust_uses` | Changes a node's remaining use count | `handle_adjust_uses` |
| `end_scenario` | Sets `scenario_ended = True` | `handle_end_scenario` |
| `restart_scenario` | Sets both `scenario_ended` and `_restart_requested` | `handle_restart_scenario` |
| `apply_condition` | Applies a condition (e.g. poisoned) to target | `handle_apply_condition` |
| `remove_condition` | Removes a condition from target | `handle_remove_condition` |
| `apply_trait` | Adds a trait to target character | `handle_apply_trait` |
| `remove_trait` | Removes a trait from target character | `handle_remove_trait` |
| `destroy_self` | Removes the triggering item from the graph | `handle_destroy_self` |
| `consume_item` | Removes a named item from player inventory | `handle_consume_item` |
| `set_description` | Replaces the description on a target node | `handle_set_description` |
| `append_description` | Appends text to a target node's description | `handle_append_description` |
| `schedule_trigger` | Queues the target's `on_delayed` trigger to fire N ticks from now (`delay_ticks`, optional `target` name/ID — default the triggering item). Pure scheduling: what happens is defined by the target's `on_delayed` trigger, so one `on_delayed` blueprint can drive any curse/timer source | `handle_schedule_trigger` |

## Delayed Events (task-90)

`engine/event_queue.py` holds a `DelayedEventQueue` on the engine (`world.delayed_events`). The `schedule_trigger` effect appends an entry `{fire_tick, target_node_id, trigger_type, label}`; `TickManager.tick_turn()` pops due events **after the clock advances** (so a 5-tick delay fires on the 5th subsequent turn) and runs the target node's `on_delayed` triggers through the normal `_execute_triggers` pipeline. If the target node was removed before the fire, the event is silently dropped. The queue is serialized in `to_dict()`/`load_from_dict()` so scheduled events survive save/load (`to_scenario_dict()` strips it as a play artifact).

## Trigger Execution Flow

The main entry point is `TriggerSystem._execute_triggers()` (`trigger_system.py:760`):

```
TriggerSystem._execute_triggers(item_node, trigger_type, target_name, context, game_state)
```

### Step-by-step:

1. **Build Template Context** (lines 807-858): Auto-populates a `context` dict with `game_time`, `time_ticks`, `player_name`, `area_name`, `item_name`, `item_state`, `item_description`, `item_properties`, `item_params`, `player_hp`, `player_energy`, `player_sanity`, `area_light`, `area_temp`, `area_smell`. Used for `{variable}` template rendering.

2. **Walk Trigger Edges** (line 861): Gets all `EDGE_TRIGGERS` edges from the item node.

3. **Filter by Trigger Type** (lines 868-891): Checks if the edge's `trigger_type` property matches the current action. Supports both single-string and list values.

4. **Filter by Target State** (lines 894-908): For `on_state_enter`/`on_state_exit`, matches against `expected_target_state` and the edge's `target_state` property.

5. **Resolve Conditions** (lines 911-920): Lookup chain:
   - Edge properties `conditions` → Trigger node properties `conditions` → Edge property `condition` (singular, legacy) → empty list

6. **Resolve Effects** (lines 923-937): Lookup chain:
   - Edge properties `effects` → Trigger node properties `effects` → Single effect from edge `effect_type` + `effect_params` (legacy)

7. **Evaluate Conditions** (lines 939-990): Supports AND/OR logic via `conditions_logic` property. Each condition is evaluated by `_evaluate_trigger_condition()`. If conditions fail, an optional `fail_message` from the effect params is rendered.

8. **Execute Effects** (lines 992-1042): Iterates all effects in order. Supports **tag-based targeting** — if `target_tag` is set in params, the effect is applied to ALL items in the room matching that tag (and optionally a `require_status`).

## Template Rendering

`_render_template()` in `trigger_system.py:103` supports `{variable}` placeholders:

- `{variable_name}` — direct lookup in context dict
- `{param:<key>}` — lookup in `item_params` (item's `parameters` property)
- `{prop:<key>}` — lookup in `item_properties` (item's `properties` dict)

Unrecognized variables are left unchanged.

## Conditions on Triggers

Individual trigger conditions are evaluated by `_evaluate_trigger_condition()` (`trigger_system.py:138`). Supported condition types:

| Condition Type | Parameters | Description |
|---|---|---|
| `uses_reached` | `value` (int) | True when item uses ≤ value |
| `uses_above` | `value` (int) | True when item uses > value |
| `has_item` | `value` (item name) | True if player has item in inventory |
| `has_items` | `value` (list) | True if player has ALL specified items |
| `state_equals` | `target`, `value`, or `value=state` | True if target node's `current_state` matches |
| `random_chance` | `value` (0-100) | True randomly X% of the time |
| `skill_check` | `skill`, `dc` | True if skill check succeeds |
| `save_throw` | `stat` or `skill`, `dc`, `target` (default `self`, or a character name) | True if the target's save succeeds — success means they resisted/avoided the event, so the trigger's effects fire. The editor offers a Base Stat / Skill toggle. The `[Save] ...` roll is surfaced in the trigger output (task-159) |
| `area_temp` | `value` (temp), `operator` (`lt`/`le`/`eq`/`ge`/`gt`) | True if room temp compares to value. Replaces `temperature_below`/`temperature_above` (still accepted as `lt`/`gt` aliases) |
| `vital` | `stat`, `value`, `operator`, `target` | True if the player's vital compares to value. Replaces `vital_above`/`vital_below` (kept as `gt`/`lt` aliases) |
| `is_equipped` | `item`, `target` | True if the player has the item equipped |
| `time_of_day` | `value` (HH:MM) | True if the current game clock matches |
| `weather` | `value` | True if the area environment's `weather` key matches |
| `has_trait` | `value` (trait ID), `target` (default `self`, or a character name) | True if the player has the trait |
| `has_tag` | `value` (tag or list of tags — any-of), `target` (`self`/blank = actor, `target` = the used-on node of an `on_use_on`, or a character name) | True if the target has any of the tags. With `target: "target"` it checks the **used-on** node (way/item/area/character) — the keycard/clearance pattern ("unlock only if the door has `clearance-4`"). The target resolves by name with exit-direction matching for doors. Editor value is a tag multiselect |
| `speech_matches` | `phrase`, `mode` (`contains`/`exact`/`startswith`/`endswith`/`fuzzy`) | True if the spoken text of an `on_speech` trigger matches |

Compound conditions (`_evaluate_conditions()` at line 311) support logical operators:

```json
{
  "operator": "and" | "or" | "not",
  "conditions": [
    {"type": "eq", "target": "item_state", "value": "open"},
    {"type": "has_item", "item": "key", "target": "player"}
  ]
}
```

Compound condition types:
| Type | Description |
|---|---|
| `eq` | Compare `target` key in context against `value` |
| `has_item` | Check if `target` has `item` in inventory |
| `in_area` | Check if `target` is in `room` |
| `random_chance` | Percentage chance |
| `tick_since_state` | Check if `min_ticks` elapsed since state entered |
| `proximity` | Check if target is within `max_areas` distance |

## Available Actions

`_get_available_actions()` (`trigger_system.py:595`) dynamically builds a list of possible interactions for an item based on:
- The item's `actions` property (comma-separated string)
- Trigger types present on the item's trigger edges
- Item `tags` (e.g., `"food"`, `"drink"`, `"openable"`)
- Current state (open vs closed affects available actions)

Always returns: `examine`
Conditional: `take`, `drop`, `open`, `close`, `use`, `use_on <target>`, `eat`, `drink`, `toggle on/off`

## Contextual Failure Messages

`_contextual_failure()` (`trigger_system.py:708`) generates first-person failure reasons:

| Verb | Default Message |
|---|---|
| `take` | "I reach for the {item} but stop — I have no need for it." |
| `use` | "I examine the {item} but can't figure out what to do with it." |
| `eat` | "I pause — that's not food." |
| `drink` | "That's not something you drink." |
| `open` | "The {item} doesn't open." |
| `close` | "The {item} isn't something you can close." |
| `break` | "I don't think breaking the {item} would accomplish anything." |

Each message appends a suggestion of available actions.

## Multi-Effect Triggers

A single trigger edge can have multiple effects in the `effects` list. Effects are executed **in order**, and all effects are processed even if some fail (no short-circuit). Example:

```json
{
  "trigger_type": "on_use",
  "effects": [
    {"type": "message", "params": {"message": "You pull the lever!"}},
    {"type": "set_state", "params": {"node_id": "way_vault", "state": "open"}},
    {"type": "damage", "params": {"amount": 5, "target": "self"}}
  ]
}
```

## Tag-Based Targeting

When an effect's params include `target_tag`, the effect is applied to **every item in the room** matching that tag (via `_get_items_by_tag_in_area()`, line 754). Additional parameters:

- `area_id` — override room (defaults to current room)
- `require_status` — filter items by `current_state` (e.g., only "lit" items)

Each matched item receives its own context with `target_item_name` and `target_item_state`.

## Unified Effect Targeting (2026-08-08)

Any effect can fan out to a set of targets with `target_by` + `target_value` (+ optional `target_scope: "area" | "world"`, default `area`):

| `target_by` | `target_value` | Scope |
|---|---|---|
| `name` | a character/node name or id | anywhere |
| `tag` | a tag (characters matched by live `player.tags`, items by node tags) | area or world |
| `trait` | a trait id (characters only) | area or world |
| `type` | `item` / `character` (or `player`) / `way` / `area` | area or world |
| `all_in_area` | — | current area, all characters |

When targets resolve, the effect runs once per target: character targets get `target` set to their name, item/way targets get passed as `item_node`. Legacy `target_tag` still works unchanged. Example — a sneeze cloud that sickens everyone in the room:

```json
{"type": "apply_condition", "params": {
  "condition": "sick",
  "target_by": "type",
  "target_value": "character",
  "target_scope": "area",
  "duration": 5,
  "source": "sneeze cloud"
}}
```

Tests: `tests/test_trigger_system.py::TestUnifiedEffectTargeting` (6 tests).

## Auto-Trigger on Tick

Any **carried or equipped item with an `on_tick` trigger** fires it every tick during `tick_turn()` (`tick_manager.py:293`) — not just lit ones. This is the contagion pattern: a hidden `plague_miasma` carrier in someone's inventory ticks each turn and spreads `sick` to everyone in the area (see `data/library/items/plague_miasma.json`).

Toggleable items that are toggled `"on"` also trigger `on_tick` effects every tick, powering persistent effects like light sources and heating. When uses reach 0, `on_depleted` is fired and the item turns off (`tick_manager.py:304`).

In addition to carried/equipped items, **items dropped in a room** that are `lit`/`on` with `uses > 0` also burn down once per tick (area-lit-item pass): their `on_tick` fires, uses decrement, and at 0 they turn off and are removed. Permanent sources (`uses == -1`, e.g. a lit stove) never burn out.

## NPC Behavior Actions

NPC behaviors (`_execute_behavior_actions()`, line 412) support a subset of effect types:

| Action Type | Description |
|---|---|
| `message` | Output narrative text |
| `speak` | Broadcast speech to room |
| `set_npc_state` | Transition NPC state machine |
| `damage` | Deal damage to player or self |
| `heal` | Restore HP/Energy on target |
| `set_environment` | Modify room temperature/light/etc. |
| `spawn_item` | Create item in NPC's room |
| `teleport` | Move player or self to another room |
| `go` | Move NPC to a room |

## Trigger Editor (UI)

Defined in `static/js/shared/trigger-editor.js`. The frontend trigger editor allows:
- Selecting trigger type from the `TRIGGER_TYPES` list
- Adding conditions with type/value pairs
- Adding effects with type/params
- Managing success/failure messages
- Setting conditions logic (AND/OR)
- Target state filtering for state enter/exit triggers

## Related tasks

- [[dev_tasks/done/graph/task-107-id-rename-sync-and-trigger-consistency|task-107: ID rename sync and trigger consistency]]
- [[dev_tasks/review/triggers/task-15-door_trigger_events|task-15: Way trigger events]]
- [[dev_tasks/review/triggers/task-16-dymanic_trigger_templates|task-16: Dynamic trigger templates]]
- [[dev_tasks/review/triggers/task-34-generate_triggers_for_new_items|task-34: Generate triggers for new items]]
- [[dev_tasks/review/triggers/task-47-stateful_continuous_triggers|task-47: Stateful continuous triggers]]
- [[dev_tasks/review/triggers/task-50-trigger_condition_has_item_dropdown|task-50: Trigger condition has_item dropdown]]
- [[dev_tasks/review/triggers/task-51-trigger_multi_effect_conditions|task-51: Trigger multi effect conditions]]
- [[dev_tasks/review/triggers/task-52-trigger_success_fail_messages|task-52: Trigger success/fail messages]]
- [[bug_1-trigger-editor-effOpts-undefined 1|bug-1: Trigger editor effOpts undefined]]
