# Items Overview

## Item Class (`item.py`)

The `Item` class (`virtual_world/item.py:2`) is a simple data class that was historically used to create item instances. In the current architecture, items are stored as `Node` objects in the `WorldGraph` (`virtual_world/graph.py:8`), and the `Item` class is used mainly for legacy compat and as a reference for what properties an item node should carry.

```python
class Item:
    def __init__(self, name, description, actions, uses=-1, effect_target=None,
                 effect_stat=None, effect_amount=0, action_costs=None):
```

## Item Node Properties

Items in the graph are `Node` objects with `type="item"` (`virtual_world/graph.py:11`). All item data lives in the `properties` dict:

| Property | Type | Default | Description |
|---|---|---|---|
| `name` | str | — | Display name (e.g. "Brass Key", "Crisp Red Apple") |
| `description` | str | `""` | Text shown on examine |
| `actions` | list[str] or str | — | Comma-separated or list: `examine,take,use,eat` |
| `uses` | int | `-1` | `-1` = infinite, `>0` = remaining uses before consumed |
| `weight` | float | `0.1` | Item weight (UI display only, no weight limit system) |
| `hidden` | bool | `false` | If `true`, item is invisible until discovered via `fumble_around()` |
| `action_costs` | dict | `{}` | Per-action cost overrides, e.g. `{"use": {"time": 2, "energy": 5}}` |
| `skill_check` | dict | `{}` | Skill check required to interact: `{"skill": "Perception", "dc": 12}` |
| `effect_target` | str or null | `null` | `"player"`, `"self"`, `"room"`, `"connection"` |
| `effect_stat` | str or null | `null` | e.g. `"HP"`, `"light"`, `"smell"` |
| `effect_amount` | int or str | `0` | Amount or value (strings used for environment overrides like `"lavender"`) |
| `tags` | list[str] | `[]` | Tags like `"food"`, `"key"`, `"toggleable"`, `"weapon"`, `"container"`, `"two_handed"`. **Planned**: migrate to `list[dict]` with `name`, `type`, `description` per [[dev_tasks/done/items/task-108-tags-as-dicts-with-type-and-description|task-108]] |
| `equip_slots` | list[str] | `[]` | Which body slots this item can be equipped to (e.g. `["head"]`, `["hand_left", "hand_right"]`). **Convention (2026-08-21)**: every item tagged `clothing` or `armor` must carry at least one slot, primary first (`_get_slot_for_item` uses `equip_slots[0]`); extra slots declare additional coverage (jumpsuit: `["torso", "arms", "legs"]`). All 60 wearables in the library are compliant; backfilled via `tools/fix_item_equipment.py` |
| `defense` | int | `0` | Damage reduction when equipped (requires `armor`/`clothing` tag) |
| `damage` | int or string | `0` | Weapon damage — accepts dice notation `"2d6+3"`, `"1d8"`, or a flat number `8` (requires `weapon` tag) |
| `damage_skill` | string | — | Skill name for damage modifier stat lookup, e.g. `"Athletics"` → STR (requires `weapon` tag) |
| `damage_type` | string | — | Damage type for resistance checks, e.g. `"slashing"`, `"fire"` (requires `weapon` tag) |
| `insulation` | int | 0 | Shifts effective ambient temp by N°C (+warm, -cool). Stacks across worn items |
| `resistances` | dict[str, int] | `{}` | Type-based damage resistances, e.g. `{"fire": 5, "cold": 3}` (requires `resistance` tag) |
| `current_state` | str | `"normal"` | State used by triggers: `"normal"`, `"locked"`, `"open"`, `"closed"`, `"lit"`, etc. |
| `library_id` | str | — | Reference back to the library item ID when built from the library |
| `triggers` | list[dict] | — | Library-only; converted to `EDGE_TRIGGERS` edges when placed in world |
| `contents` | list | `[]` | **UI-only.** See "Container Items" below. |

### Example: Apple (`data/library/items/apple.json`)

```json
{
  "name": "Crisp Red Apple",
  "description": "A crisp red apple, cool from the cellar. Looks fresh and sweet.",
  "actions": "examine,take,use,eat",
  "uses": 1,
  "weight": 0.2,
  "hidden": false,
  "tags": ["food", "fruit"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effect_type": "heal",
      "effect_params": { "amount": 5, "message": "You bite into the sweet apple." }
    }
  ]
}
```

### Example: Candle (`data/library/items/candle.json`)

```json
{
  "name": "candle",
  "description": "An unmarked black candle...",
  "actions": "examine,take,use",
  "uses": 10,
  "weight": 0.3,
  "effect_target": "room",
  "effect_stat": "light",
  "effect_amount": 35,
  "action_costs": { "use": { "energy": 0, "time": 1 } }
}
```

## Node ID Conventions

From `virtual_world/.opencode/AGENTS.md:68-75` and `engine/node_ids.py`:

- `item_<name>` — e.g. `item_rusty_key`, `item_Brass Key`
- Area names normalized: lowercase, spaces → underscores via `_area_node_id()`
- Item IDs are generated `item_<name>` via `NodeIDHelper.item_node_id(name)` (`virtual_world_engine.py:226`)
- When `add_node()` detects a duplicate item ID, a random 8-char UUID suffix is appended (`graph.py:51-57`)

## Item Placement

Items exist in the world graph through edge relationships:

### In a Room
`EDGE_IN = "in"` edge from item node → room node (`graph.py:201`)
```python
Edge(source="item_rusty_key", target="area_living_area", type="in")
```

### In a Player's Inventory
`EDGE_CARRYING = "carrying"` edge from item node → player node (`graph.py:207`)
```python
Edge(source="item_rusty_key", target="player_traveler", type="carrying")
```

### Spatial Positioning (Replaces `EDGE_CONTAINS`)
Items in or on containers use spatial `EDGE_IN`, `EDGE_ON`, `EDGE_UNDER`, `EDGE_BEHIND`, `EDGE_BESIDE`, or `EDGE_AT` edges (`graph.py:201-206`). The old `EDGE_CONTAINS` and `EDGE_LOCATION` constants are deprecated — container contents are now expressed with directional positioning. The `contents` property on items is informational only (used by UI). Actual container contents must be spawned via triggers (`spawn_item` effect).

## Item States

### Toggleable On/Off
Items with `"toggleable"` in their `tags` can be toggled on/off via `toggle <name>`. State tracked in `player.item_statuses` (`player.py:103`), a dict of `{item_node_id: "on"|"off"}`.

### Uses Remaining
The `uses` property controls consumability:
- `-1`: Infinite uses (never consumed)
- `>0`: Decremented each use. When it reaches 0, the item is removed from the graph.

Handled in `item_actions.py:502-511`, `item_actions.py:601-611`, and `tick_manager.py:287-308`.

### Progressive Item Status (`current_state`)
Items can have arbitrary states like `"normal"`, `"locked"`, `"lit"`, `"open"`, `"closed"`. State transitions fire `on_state_exit` and `on_state_enter` triggers (`effects.py:220-238`).

The examine handler checks for `current_state == "locked"` and shows a `locked_message` (`item_actions.py:81-83`).

## Item Actions

Every item has an `actions` property (comma-separated string or list) that defines what verbs work on it:

| Action | Method | Description |
|---|---|---|
| `take` | `ItemActions.take_item()` (`item_actions.py:172`) | Pick up from room to inventory |
| `drop` | `ItemActions.drop_item()` (`item_actions.py:370`) | Drop from inventory to room |
| `examine` | `ItemActions.get_item_desc()` (`item_actions.py:28`) | Describe item/details |
| `use` | `ItemActions.use_item()` (`item_actions.py:519`) | Activate item (triggers, effects) |
| `eat` | `ItemActions.eat_item()` (`item_actions.py:418`) | Consume as food |
| `drink` | `ItemActions.drink_item()` (`item_actions.py:421`) | Consume as drink |

The `take_item` flow (`item_actions.py:364-...`):
1. Ghost check → state check → light check
2. Find item in room (exact → word-boundary → alias → fuzzy → inside containers)
3. Check "take" in item actions
4. Optional skill check
5. Execute `on_take` triggers
6. Remove `EDGE_IN` edge, add `EDGE_CARRYING` edge
7. Register item discovery (+Entertainment, task-136)
8. Apply action costs
9. Record turn event

### Duplicate items & selection

Multiple items can share the same display name (e.g. two Jumpsuits placed from the same library item). They are distinguished by **unique node ids** — `WorldGraph.add_node` appends a random 8-char suffix to a duplicate id (`graph.py:51-57`), and `/api/build/item-from-library` (`routes/library_routes.py`) generates unique ids up front. Display names stay identical.

When a `take` (or `use`/`drop`) resolves to several matches:

- **Identical copies** (same name, description, tags, state — e.g. two jumpsuits from the same library item) are **auto-selected**: the engine picks the first without asking (`_auto_select_identical`, `item_actions.py:345`).
- **Distinct items** still raise `AmbiguousItemError` → the UI shows a numbered "Which one?" prompt.
- `take <name> <n>` picks the *n*-th match; the number branch is **case-insensitive with fuzzy fallback** (`routes/action.py`), matching the resolver's behavior.

> **Note**: placements snapshot the library entry at build time. Fix a library item's props (e.g. `equip_slots`) and propagate to already-placed nodes with `POST /api/items/<node_id>/refresh-from-library` (needs `library_id`; bug_14).

The `drop_item` flow (`item_actions.py:370-416`):
1. Ghost check → state check
2. Find item in inventory (EDGE_CARRYING)
3. If equipped, remove from equipment slot (unequip)
4. Execute `on_drop` triggers
5. Remove `EDGE_CARRYING`, add `EDGE_IN`
6. Apply action costs

The `use_item` flow (`item_actions.py:519-615`):
1. Ghost check → state check
2. Find item in inventory
3. Check "use" in actions OR presence of trigger edges
4. Execute triggers (both `on_use` and type-specific)
5. Skill check
6. Apply action costs
7. Apply effect (self/player/room)
8. Decrement uses → remove if depleted

## action_costs on Items

Items can specify per-action cost overrides via `action_costs` (`item.py:9`). Format:
```json
{ "use": { "time": 2, "energy": 5 } }
```

These are passed through `player_manager.apply_action()` in `tick_manager.py:14-46`, which merges them with base costs from `ACTION_COSTS` in `virtual_world_engine.py:77-86` and applies trait modifiers.

## Item Matching

The `NameMatching` class (`engine/matching.py:10`) provides four-tier matching:

1. **Exact match** (case-insensitive)
2. **Word-boundary substring** — input must appear as a whole word inside a name (and vice versa). Raw substring is NOT used, so `stove` no longer matches `Stovepipe Leather Boots (Pair)`. Inputs shorter than 2 chars are rejected before this tier.
3. **Alias match** — input matches an item's `aliases` property (e.g. `kindling` has aliases `["twigs", "dry twigs", "firewood"]`). Aliases survive save/load (`serialization.py`) and the items registry.
4. **Fuzzy difflib** (cutoff 0.7 for items, 0.6 for exits)

`_is_item_reachable()` (`matching.py:133-160`) checks:
- Directly in the room (EDGE_IN from room)
- In player inventory (EDGE_CARRYING from player)
- Inside an examined (unhidden) container in the room
- Inside an examined (unhidden) container in player inventory

### Flavor Targets (background objects)

Objects that only exist in description text (a stove, a loose tile, the moon) are
handled **narratively**, not as items. After real item/exit/character resolution
fails, `examine` falls back to `_describe_flavor_target()` and `use X on Y` falls
back to `_descriptive_target_failure()` (`item_actions.py:181`, `:948`), which scan
the area + item + way descriptions for the phrase and return an in-character
response ("You examine the stove, but it does not seem to be of any use."). Flavor
is the **last resort**, so it can never block a genuine target.

### `use X on Y` target parsing

`routes/action.py` takes the **full remainder after `on`** as the target — never a
single token — so `use create flame on dried flower crown` targets the whole crown
instead of truncating to "dried". Quoted tokens after `on` are treated as an explicit
target + optional params pair (e.g. `use quill on "letter" "some text"` → inscribe),
tracked by `tokenize_command_detailed` (`routes/helpers.py`).

## Container Items

Container items (with `"container"` tag) use spatial `EDGE_IN`/`EDGE_ON`/`EDGE_UNDER`/`EDGE_BEHIND`/`EDGE_BESIDE`/`EDGE_AT` edges. The old `EDGE_CONTAINS` constant is deprecated — container contents are now expressed with directional positioning. The `contents` property on items is UI-only — actual spawning happens via triggers using the `spawn_item` effect.

Container items are referenced in:
- `get_item_desc()` at `item_actions.py:102-110` — shows contents when examining an unlocked container
- `take_item()` at `item_actions.py:260-310` — allows taking items from inside containers

## spawn_item Triggers

The `spawn_item` effect (`effects.py:143-175`) creates items in the current room:
- Looks up `params.get("item_id")` and creates a bare Node with `type="item"`
- Places via `EDGE_IN` edge
- Items spawn **without** trigger edges — for `on_use_on` behavior, rely on the legacy `locked_with` path

## locked_with Legacy Path

When a key item is used on a door (`use_item_on` at `item_actions.py:693-701`):
1. Finds the door node from the matched exit direction
2. Checks for `EDGE_UNLOCKS` edges from item → door (`graph.py:172`): `Edge(source=item_id, target=way_id, type="unlocks")`
3. If found, sets door state to `"closed"`
4. Also checks `effect_target == "connection"` for direct state changes (`item_actions.py:703-709`)

## Item Library (`routes/library_routes.py`)

The item library stores reusable item definitions in `data/library/items/*.json`. The `/api/build/item-from-library` endpoint (`routes/library_routes.py`) converts library items to world items:
1. Looks up item in library by `item_id`
2. Creates/updates a `Node(id="item_<name>", type="item")` with properties copied from library data
3. Places in the target room/container/character
4. Converts library `triggers` array to `EDGE_TRIGGERS` edges with `logic_trigger` nodes

Library items support all properties listed above plus:
- `triggers`: Array of trigger definitions with `trigger_type`, `effect_type`, `effect_params`, `target_name`, `condition`

## Tags

Tags are a core query system ([[dev_tasks/done/items/task-98-tags-as-core-query-system|task-98]]). They classify items for engine behavior, triggers, and UI display. See the [[Library System/Tags System|Tags System]] page for the full list of mechanical tags.

### Current shape: `list[str]`

Each tag is a lowercase string. All engine checks use simple `in` membership:

| Tag | Used by | Effect |
|---|---|---|
| `"toggleable"` | `toggleable_items.py:27` | Grants ability to toggle on/off |
| `"two_handed"` | `equipment.py:62` | Occupies both hand slots |
| `"equips_all_slots"` | `equipment.py:70` | Occupies every slot in `equip_slots` (full-body suits) |
| `"food"` | `trigger_system.py:688`, `item_actions.py:444` | Enables `eat` action |
| `"drink"` | `trigger_system.py:691`, `item_actions.py:446` | Enables `drink` action |
| `"openable"` | `trigger_system.py:642` | Enables `open` action |
| `"container"` | `item_actions.py:102-110` | Shows contents on examine |
| `"weapon"`, `"armor"`, etc. | `item-library.js:109-134` | UI type icon and color |

### Tag query methods (`graph.py:94-154`)

- `get_items_by_tag(tag, area_id?)` — find items by tag, optionally in a room
- `get_characters_by_tag(tag, area_id?)` — find characters by tag
- `get_tagged_items_in_area(area_id, exclude_tags?)` — all items in room grouped by tag
- `get_items_by_tag_and_status(tag, status, area_id?)` — items matching tag + `current_state`

### Tag-based targeting in triggers

Trigger effects can use `target_tag` to apply to ALL items in the room matching a tag ([Triggers & Effects](Rules%20Engine/Triggers%20&%20Effects.md) lines 219-226).

### Planned: rich tags ([[dev_tasks/done/items/task-108-tags-as-dicts-with-type-and-description|task-108]])

Tags are planned to migrate from `list[str]` to `list[dict]` with `name`, `type`, and `description` fields. This will separate **mechanical tags** (two_handed, toggleable) from **category tags** (magic, fantasy, book). A companion tag library ([[dev_tasks/inprogress/items/task-106-tag-library-and-multiselect|task-106]]) will define metadata centrally.

## Hidden Items

Items with `"hidden": True` are invisible to `look` and require a Perception check via `fumble_around()` to discover. The discover flow (`fumble_around` in `engine/movement.py`) sets `hidden = False` for all items in the room that are hidden.

## Weight System

The `weight` property exists on items (`Item.__init__`, `item.py`) but there is **no weight limit system** — players can carry unlimited items. Weight is UI display only. A weight/volume system is planned ([[dev_tasks/review/items/task-103-weight-volume-container-limits|task-103]]).

## Related tasks

- [[dev_tasks/done/items/task-98-tags-as-core-query-system|task-98: Tags as core query system]]
- [[dev_tasks/todo/ui/task-6-item_interaction_context_menu|task-6: Item interaction context menu]]
- [[dev_tasks/todo/items/task-9-procedural_item_placement|task-9: Procedural item placement]]
- [[dev_tasks/review/ui/task-13-unify_item_inspector_and_library|task-13: Unify item inspector and library]]
- [[dev_tasks/todo/items/task-102-progressive-item-status-multi-use|task-102: Progressive item status multi-use]]
- [[dev_tasks/review/items/task-103-weight-volume-container-limits|task-103: Weight volume container limits]]
- [[dev_tasks/todo/gameplay/task-104-multi-action-command-sequences|task-104: Multi-action command sequences]]
- [[dev_tasks/inprogress/items/task-106-tag-library-and-multiselect|task-106: Tag library + multiselect]]
- [[dev_tasks/done/graph/task-107-id-rename-sync-and-trigger-consistency|task-107: ID rename sync and trigger consistency]]
- [[dev_tasks/done/items/task-108-tags-as-dicts-with-type-and-description|task-108: Tags as dicts with type and description]]
- [[dev_tasks/review/items/task-19-food_items_eat_action|task-19: Food items eat action]]
- [[dev_tasks/review/items/task-21-item_parameters_system|task-21: Item parameters system]]
- [[dev_tasks/review/items/task-29-create_item_container_support|task-29: Create item container support]]
- [[dev_tasks/review/items/task-32-enhanced_item_creation|task-32: Enhanced item creation]]
- [[dev_tasks/review/environment/task-33-generate_item_room_context|task-33: Generate item room context]]
- [[dev_tasks/review/triggers/task-34-generate_triggers_for_new_items|task-34: Generate triggers for new items]]
- [[dev_tasks/review/items/task-53-use_item_with_parameters|task-53: Use item with parameters]]
- [[bug_6-inspector-equip-slots-white-bg 1|bug-6: Inspector equip slots white bg]]
