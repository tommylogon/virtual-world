# Item & Action Model

The item/action model is a single graph-based truth: every item is a `Node` of `type="item"`, and what a character can do to it is decided by three things in order — the item's advertised `actions`, whether it is **reachable** given the character's position, and whether it is **portable** (i.e. not a fixed part). This page collects those rules so they are discoverable without reading code.

## 1. The `actions` list is the capability gate

An item node's `actions` property — a list or comma-separated string — is the gate for what can be done to or with it. Every verb that *moves* an item asks one question: is the item portable? Portability is defined as the item declaring `take` in its own `actions` list, so the gate is consulted from a single function rather than scattered across verbs:

```python
# engine/items/action_contract.py:36-45
def is_portable(node) -> bool:
    """True when *node* may be picked up, moved, dropped, stolen or put away."""
    return item_allows("take", node)
```

`take_item` is the worked example. It reads the actions list and raises when `take` is absent:

```python
# engine/items/take_drop_actions.py:602-607
item_actions = item_node.properties.get("actions", [])
if isinstance(item_actions, str):
    item_actions = [a.strip() for a in item_actions.split(",")]
if "take" not in item_actions:
    available = self.trigger_system._get_available_actions(item_node)
    raise ValueError(self.trigger_system._contextual_failure("take", item_node.name, available))
```

The same `is_portable()` gate is consulted by every other moving verb, so a non-portable item is untakeable, undroppable, un-puttable, un-giveable, and un-stealable (`take_drop_actions.py:826`, `place_actions.py:52` and `:138`, `transfer_actions.py:66` and `:172`). Before task-493 only `take` read the list, which left a part untakeable but still droppable — the gate is now universal.

### Action tokens in use

Across `data/library/items/*.json` the following tokens appear in the `actions` property. `normalize_item_actions` (`engine/item_actions.py:50-63`) auto-adds each action's inverse (take↔drop, equip↔unequip, open↔close), so an author only has to declare one direction:

| Token | Verb(s) | How it is read |
|---|---|---|
| `examine` | examine | Always appended in `_get_available_actions` (`engine/triggers/ui.py:48-54`); never refused |
| `take` | take | `take_drop_actions.py:605` — absent → raise |
| `drop` | drop | Derived from `take` via inverse; `is_portable` at `take_drop_actions.py:826` |
| `use` | use, use-on | `use_actions.py:112` (`"use" in item_actions or has_any_trigger`); `:294` adds `on_use_on` trigger check |
| `eat` | eat | `consume_actions.py:85` (`"eat" in actions or "food" in tags`) |
| `drink` | drink | `consume_actions.py:87` (`"drink" in actions or "drink" in tags`) |
| `open` | open | `triggers/ui.py:68`; tag `openable` is an alternative |
| `close` | close | `triggers/ui.py:81`; auto-added by inverse from `open` |
| `equip` | equip | `EquipmentSystem.equip_item` requires `equip_slots`; inverse auto-adds `unequip` |
| `unequip` | unequip | Inverse of `equip` |
| `read` | read (via use) | No direct verb; `use_actions.py:148` falls back to `on_read` triggers when `on_use` produces nothing |
| `repair` | repair (NPC) | Dispatched in `engine/triggers/behaviors.py:512`; no player verb yet |
| `oil` | informational | No handler; informational only |

The read entry point is `engine/items/action_contract.py:item_actions()` (`action_contract.py:22-28`), which normalises either a list or a comma-separated string into a stripped list. Absent the `actions` property means "nothing declared."

## 2. Reach rules

What makes an item reachable is in `engine/item_reach.py` — a single module consulted by use, use_on, eat, drink, place, and toggle so every verb agrees on "the thing right there." The rule, in priority order:

1. **Carried or equipped** — the item is on an `EDGE_CARRYING` or `EDGE_EQUIPPED` edge to the player node (`item_reach.py:177-184`). Carried wins first via `find_reachable` (`item_reach.py:111-119`).
2. **Inside a carried/equipped container that isn't closed** — the container is reachable and `_is_open()` passes (`item_reach.py:65-69`, `_CLOSED_STATES` at `:23`). Contents are walked to any nesting depth (`item_reach.py:147-157`, recursive `walk`).
3. **In the current area** — directly, or placed on/under/beside/behind/at a surface. Spatial edges (`EDGE_ON`, `EDGE_UNDER`, `EDGE_BEHIND`, `EDGE_BESIDE`, `EDGE_AT`) are expanded by `get_edges_for_target(area, EDGE_IN)` in `graph.py:120-124`.
4. **Inside an open container in the area**, at any nesting depth (open container walk, `:156-157`).

Hidden items are pruned: `current_state == "hidden"` is invisible until examined (`item_reach.py:57-62`). Closed/locked/sealed containers remain visible but seal their contents (`_CLOSED_STATES` at `:23`; `_is_open` at `:65-69`).

The spatial half is `engine/character_spatial.py`: position is a *relation*, not coordinates. A character holds exactly one `EDGE_AT` edge at a time (`enforce_single_at` at `character_spatial.py:158-181`), and proximity to nearby objects is derived by walking the `beside`/`on`/`under` edge graph (`proximity_hops` at `:257-291`). `approach_item` (`character_spatial.py:670-691`) is the setter that verbs call before interacting with an area item.

## 3. Depletion branching — the generic `use` path

When `uses` drains to zero, the outcome is decided by what kind of item it is. The entry point is `use_item` (`engine/items/use_actions.py:207-212`), which decrements `uses` and calls `_depleted_by_use` when the count hits zero:

```python
# engine/items/use_actions.py:207-212
uses = item_node.properties.get("uses", -1)
if uses > 0:
    uses -= 1
    item_node.properties["uses"] = uses
    if uses == 0:
        result += self._depleted_by_use(item_node)
```

`_depleted_by_use` (`use_actions.py:27-62`) branches on `is_part`:

| Branch | Condition | Outcome | Code |
|---|---|---|---|
| **Generic use detaches** | `not is_part(node)` | The placement `EDGE_IN` is cut; the node leaves the scene | `use_actions.py:48-52` |
| **Part runs unlit** | `is_part(node)` (non-portable child) | `current_state` set to `"unlit"` (if not already spent); `on_depleted` fires first as an escape hatch; node stays in place | `use_actions.py:54-62` |

The same teardown is reached by the consume path. `_deplete_if_spent` (`engine/items/consume_actions.py:151-163`) fires on the `uses_before > 0 → 0` transition and delegates to `_finish_depleted` (`:165-188`), which runs `on_depleted`, then removes the node unless it marked itself with a persistent empty state (`PERSISTENT_EMPTY_STATES` at `consume_actions.py:9-13`).

Two other depletion paths exist outside the generic `use` function:

- **Lit item in an area burns out** — `TickManager._burn_down_area_item` (`engine/tick_manager.py:353-365`): a lit (`"lit"`/`"on"`) standing item with finite `uses` is ticked, goes `"unlit"`, fires `on_depleted`, and is removed from the graph. Permanent sources (`uses == -1`) never burn out (`tick_manager.py:356-357`).
- **Armor breaks on hit** — `EquipmentSystem.increment_armor_uses_on_hit` (`engine/equipment.py:570-631`): the outermost armor/clothing item with `uses > 0` is decremented; at zero it is unequipped to carrying, fires `on_break`, and reports the break narratively (`equipment.py:614-622`, `_break_equipped_item` at `:633-641`).

## 4. Container nesting

Containment is a graph edge, not a node sub-tree. A container's contents are the set of nodes that hold an `EDGE_IN` edge pointing *into* it (`graph.py:579`). Nesting is arbitrary depth — the graph is walked recursively:

- `carry_weight.py` `_sum_container_contents` (`:29-40`) recurses through every nested `EDGE_IN`, applying `container_weight_mod` at each level.
- `item_reach.py` `_visible_ordered` `walk` (`:147-157`) recurses through open containers at any depth.

A pooled resource (`quantity > 1` or a `harvest` spec) is treated as a *pool*, not a stackable twin — `stackable_twins` (`engine/items/stacking.py:45-47`) returns `False` for any node with `quantity > 1`, and `take` spawns real copies instead of moving the node (`take_drop_actions.py:629-630`).

Capacity on a container is a soft guard checked before placement: `_check_container_capacity` (`engine/item_actions.py:130-150`) reads `max_weight_capacity` from the container node, sums nested contents weight, and raises if the item would exceed it. Containers in the reference scenario carry this property (e.g. `data/scenarios/kraktooth_goblin_camp.json:17062`, `data/scenarios/taco_bell_date.json:1888`).

## 5. The part / component model (task-493)

A **part** is an ordinary item node that happens to be a child of a parent item, and the only thing that marks it as a component is that it does **not** declare `take` in its `actions`. There is no new edge type, no `is_part` flag, and no `device_type` field — containment is a plain `EDGE_IN` edge, and the contract is:

```
# engine/items/action_contract.py:48-54
def is_part(node) -> bool:
    """True when *node* is a non-portable child item — a component of
    something larger, rather than a thing in its own right."""
    return node is not None and not is_portable(node)
```

Four rules make this coherent (documented at `action_contract.py:3-17`):

1. **The action list is the single authority on portability.** `take` is the load-bearing verb (`action_contract.py:36-45`); every moving verb asks `is_portable`. Since `normalize_item_actions` auto-adds inverses, a part must omit *both* `take` and `drop`.
2. **A part is still reachable and usable.** `item_reach.find_reachable` walks any depth regardless of portability (`item_reach.py:100-137`), so a battery inside a carried phone is addressable. Portable and reachable are not opposites.
3. **Depletion does not detach a part.** When a part runs flat it goes `unlit` and fires `on_depleted` instead of being cut free (`use_actions.py:48` — the `not is_part` branch skips parts).
4. **`parent_of` resolves the device.** `action_contract.py:57-67` walks `EDGE_IN` edges to find the parent item node, and `portable_refusal` (`action_contract.py:70-82`) names the device in the refusal so the player knows what they are trying to pry loose.

The contract is fully implemented in code — `is_portable`, `is_part`, `parent_of`, and `portable_refusal` all exist and are wired into `take`, `drop`, `put`, `place`, `give`, and `steal`. A phone with a detachable battery would declare `examine,take,drop,equip,unequip` on its `actions` and list the battery in `contents` (UI-only); the battery would declare `examine,use` only (`action_contract.py:4-6`).

## Where the rules live

| Module | Responsibility |
|---|---|
| `engine/items/action_contract.py` | Portability contract: `is_portable`, `is_part`, `parent_of`, `portable_refusal` |
| `engine/items/take_drop_actions.py` | take, drop, stow; placement-edge capture/retarget (task-407) |
| `engine/items/use_actions.py` | use, use-on; depletion branching via `_depleted_by_use` |
| `engine/items/consume_actions.py` | eat, drink; charge spend (`_spend_uses`), depletion (`_deplete_if_spent`, `_finish_depleted`) |
| `engine/items/place_actions.py` | put-in-container, place-on-surface; placement-edge cleanup |
| `engine/items/transfer_actions.py` | give, steal; character-to-character transfer with portability gate |
| `engine/items/ownership.py` | `owner` / `personal` permission model; `permission_refusal` |
| `engine/items/stacking.py` | combine / split stackable instances; `stackable_twins` |
| `engine/items/carry_weight.py` | encumbrance math; `BASE_CARRY_CAPACITY`, `sum_carry_weight`, container capacity |
| `engine/item_reach.py` | `find_reachable`, `reachable_items`; the single reachability rule |
| `engine/character_spatial.py` | spatial edges, one-`at` invariant, proximity, approach helpers |
| `engine/toggleable_items.py` | lit/unlit state flip; uses burn to 0 → `on_depleted` |
| `engine/equipment.py` | equip/unequip on body slots; `decrement_armor_uses_on_hit` (armor break) |
| `engine/tick_manager.py` | area-item burn-down (`_burn_down_area_item`); standing `on_tick` |
| `engine/triggers/ui.py` | `_get_available_actions`, `_contextual_failure` for the context menu |
| `graph.py:579-595` | Edge-type constants and `SPATIAL_EDGE_TYPES` |

## Related docs

- [[Items Overview]]
- [[Inventory]]
- [[Equipment & Paperdoll]]
- [[Item States & Toggleables]]
- [[Character Spatial Position]]
- [[Doors & Connections]]
- [[Triggers & Effects]]
- [[Light System]]
- [[Tags System]]
