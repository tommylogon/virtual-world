# Inventory System

## How Items Move Between Area and Player

The inventory system uses graph edges to track item location. There is **no** `inventory` list on the `Player` object that's used for gameplay — the legacy `Player.inventory` property (`player.py:81`) is present but not consulted by any engine code for inventory operations.

### Graph Edge Model

- Items in a room: `EDGE_IN = "in"` edge from item node → room node (`graph.py:201`)
- Items carried by player: `EDGE_CARRYING = "carrying"` edge from item node → player node (`graph.py:207`)

When you `take` an item, the edge is moved:
```python
# Remove from room
self.graph.remove_edge(item_node_id, area_id, EDGE_IN)
# Add to player
self.graph.add_edge(Edge(source=item_node_id, target=player_id, type=EDGE_CARRYING))
```
(`item_actions.py:347-349`)

When you `drop` an item, the reverse happens:
```python
# Remove from player
self.graph.remove_edge(item_node_id, player_id, EDGE_CARRYING)
# Add to room
self.graph.add_edge(Edge(source=item_node_id, target=area_id, type=EDGE_IN))
```
(`item_actions.py:403-405`)

## take Command

**Command**: `take <item_name>` (aliases: `get`, `grab`, `snatch`, `collect`, `pickup`, `pick up`, `pick` — normalized in `action.py:67-84`)

**Backend**: `ItemActions.take_item()` (`engine/item_actions.py:172`)

The full flow:

1. **Ghost check**: Dead players can't take items unless ghost mode is on (`item_actions.py:177-180`)
2. **State check**: Can't take while `sleeping`, `unconscious`, or `bound` (`item_actions.py:177`)
3. **Light check**: If ambient light < 20, raise error (`item_actions.py:185-188`)
4. **Find the item** (see "Item Resolution" below)
5. **Check "take" action**: Item must have `"take"` in its `actions` property (`item_actions.py:326-328`); uses `_contextual_failure` for contextual rejection messages
6. **Optional skill check** (`item_actions.py:330-336`)
7. **Execute `on_take` triggers** (`item_actions.py:338`)
8. **Move edge**: Remove from room/container, add `EDGE_CARRYING` to player (`item_actions.py:340-349`)
9. **Apply action costs** (`item_actions.py:352-353`)
10. **Record turn event** (`item_actions.py:356-357`)
11. **Notify NPCs**: Calls `process_simple_npcs("on_item_taken")` (`item_actions.py:364-366`)

### Ambiguous Item Handling

When multiple items share the same name, `AmbiguousItemError` is raised (`item_actions.py:7-12`). The frontend receives `{"ambiguous_items": options_list, "needs_selection": True}` and prompts the user to pick via `take <name> <number>`. This is handled in `action.py:218-226`.

### Item Resolution Priority

`take_item()` searches in this order (`item_actions.py:190-321`):

1. **Exact node ID** (if `item_id` parameter provided) — line 196-199
2. **Canonical item ID** via `player_manager.item_node_id()` + `_is_item_reachable()` — lines 201-206
3. **Exact name match** in room items (EDGE_IN from room) — lines 209-213
4. **Fuzzy name match** via `_match_item_name()` — lines 216-221
5. **Substring match** (name contains input) — lines 240-257
6. **Inside containers in room** (EDGE_IN from container node) — lines 259-283
7. **Inside containers in inventory** (EDGE_IN from container node carried by player) — lines 285-310
8. **Not found** — error with visible items list — lines 312-320

## drop Command

**Command**: `drop <item_name>`

**Backend**: `ItemActions.drop_item()` (`engine/item_actions.py:370`)

The flow:
1. Ghost check → state check
2. Find item in inventory via `EDGE_CARRYING` edges
3. **If equipped**: Remove from equipment slot first (`item_actions.py:394-399`)
4. Execute `on_drop` triggers (`item_actions.py:401`)
5. Move edge to room (`item_actions.py:403-405`)
6. Apply action costs
7. Record turn event

## examine Command

**Command**: `examine <item_name>` (aliases: `read`, `search`, `inspect`, `check` — `action.py:62-64`)

**Backend**: `ItemActions.get_item_desc()` (`engine/item_actions.py:28`)

Returns a detailed description including:
- Item description text (`item_actions.py:79`)
- Locked state message if `current_state == "locked"` (`item_actions.py:81-83`)
- Skill check details (if configured) (`item_actions.py:85-95`)
- `on_examine` trigger outputs (`item_actions.py:97-99`)
- Container contents if unlocked (`item_actions.py:101-110`) — sets `hidden = False` on contained items
- Available contextual actions (`item_actions.py:112-117`)

## use Command

**Command**: `use <item_name>` or `use <item> on <target>` (with optional `"params"` in quotes for inscribing)

**Backend**: `ItemActions.use_item()` (`item_actions.py:519`) and `ItemActions.use_item_on()` (`item_actions.py:617`)

See [[Items Overview#Item Actions]] for details.

## Inventory UI

### Backend (`action.py:230-247`)

The inventory command (`i`, `inv`, `inventory`) returns:
- Equipped items grouped by slot with `[WORN]` label
- Carried items (inventory minus equipped items)

```python
def get_inventory(self, player_manager) -> List[str]:
    player_id = player_manager._player_node_id(player_manager.active_player)
    seen = set()
    items = []
    for edge in list(self.graph.get_edges_for_target(player_id, EDGE_CARRYING)):
        node = self.graph.get_node(edge.source)
        if node and node.type == "item" and node.name not in seen:
            seen.add(node.name)
            items.append(node.name)
    return items
```
(`item_actions.py:161-170`)

### Frontend (`ApiClient in static/js/api.js`)

The `ApiClient` class fetches world state via `GET /api/state` (registered in `action.py:32`) and sends actions via `POST /api/action` (registered in `action.py:44`). Inventory display logic lives in:

- `static/js/inspector.js` — Inspector panels showing inventory
- `static/js/inspector/paperdoll-view.js` — Paperdoll + inventory context menus

### Context Menu (Right-Click)

Defined in `static/js/inspector/paperdoll-view.js:213-233`:

For inventory items, right-click shows:
- **Inspect** → opens node in Inspector
- **Equip** (if `equip_slots` is non-empty) → sends `wear <name>` command
- **Open Container** (if `"container"` tag) → opens node in Inspector
- **Drop** → sends `drop <name>` command

For paperdoll slots, right-click shows:
- **Inspect** → opens outer item in Inspector
- **Open Container** (if container tag)
- **Unequip** → sends `unequip <slot>` command

Stack expansion badges on layered slots (`paperdoll-view.js:59-62`) show `+N more` for inner layers. Click opens a popup showing all layers with individual unequip buttons.

## Weight System

The `weight` property is defined on items (`item.py:4` constructor param, serialized in `item.py`) but there is **no weight limit or encumbrance system**. Players can carry unlimited items. Weight is stored for UI display purposes only.

## Inventory Serialization

Inventory state (which player carries which items) is persisted through the graph edges. The `WorldSerializer` (`engine/serialization.py`) serializes all graph nodes and edges, so `EDGE_CARRYING` edges are preserved on save/load.

**Known issue** (`dev_tasks/my-thoughts-about-virtual-world.md:86`): `_item_active_effects` (toggleable item room effects) is NOT serialized — lost on save/load. Item statuses (`player.item_statuses`) have had serialization issues.

## Error Handling

- `ValueError` for game-logic errors → caught at route level → `{"error": "..."}`
- `AmbiguousItemError` (has `.options` list of `{id, name, description}`) for fuzzy item matching → frontend shows numbered selection
- Light level < 20 blocks examine, take, and use operations
- State-based blocks (`sleeping`, `unconscious`, `bound`, `dead`) prevent most actions

## Related tasks

- [[dev_tasks/todo/ui/task-6-item_interaction_context_menu|task-6: Item interaction context menu]]
- [[dev_tasks/review/items/task-103-weight-volume-container-limits|task-103: Weight volume container limits]]
