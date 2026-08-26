# VirtualWorld Scenario Creation Guide

Comprehensive reference for authoring scenario JSON files, usable by both humans and LLMs.
Tested against engine `serialization.py`, `trigger_system.py`, `effects.py`, and 15+ AI-generated scenarios.

---

## 1. Source of Truth: The Graph

The **only** format the engine reads at runtime is:

```json
{
  "graph": {
    "nodes": { "node_id": { "id": "...", "type": "...", "name": "...", "properties": { ... } } },
    "edges": [ { "source": "...", "target": "...", "type": "...", "properties": { ... } } ]
  }
}
```

Everything else is written by `to_dict()` as convenience views — but they are **not**
all ignorable. On load (`serialization.py` → `load_from_dict`):

| Block | Read on load? |
|---|---|
| `graph` | **Yes — source of truth** for areas, ways, items, triggers, spatial edges |
| `players` | **Yes — authoritative for characters.** Personality, vitals, skills, memories, emotion, `autonomy`, `npc_behavior` all hydrate from here; graph `character` nodes are bare anchors created empty if missing |
| `world_lore` | **Yes** — injected into every agent prompt (needs `{category, title, content}` shape) |
| `active_player`, `time_ticks`, `clock_start_*`, `turn_number`, `narration_mode`, `ghost_mode` | **Yes** |
| `areas`, `ways`, `rooms`, `item_registry`, `players_in_area` | No — pure convenience views |

**Rule: every interactive thing must be a graph node. Every relationship must be a graph edge.
Every character must exist in `players`.**

---

## 2. Node Reference

All nodes share this shape:

```json
{
  "id": "unique_node_id",
  "type": "area" | "way" | "item" | "character" | "logic_trigger",
  "name": "Human-Readable Name",
  "properties": { ... },
  "created": 1234567890.123,
  "updated": 1234567890.123
}
```

`created`/`updated` are timestamps; safe to omit or set to `0`.

---

### 2.1 Area

```json
{
  "id": "area_<slug>",
  "type": "area",
  "name": "Display Name",
  "properties": {
    "description": "Narrative description shown when player looks.",
    "environment": {
      "light": "normal",
      "temperature": 21.0,
      "air": "fresh",
      "smell": "neutral",
      "noise": "quiet"
    },
    "floor": 0,
    "tags": ["exterior", "fantasy"],
    "central_gravity_enabled": false
  }
}
```

**Environment values:**
- `light`: `"pitch_black"`, `"dim"`, `"normal"`, `"bright"`, `"blinding"`, or integer `0`–`100`
- `temperature`: float Celsius
- `air`: `"fresh"`, `"stale"`, `"musty"`, `"cold"`, `"hot"`, `"foul"`, `"toxic"`, `"thin"`, `"dense"`, `"suffocating"`
- `smell`: free text
- `noise`: free text

---

### 2.2 Way (Door / Passage)

```json
{
  "id": "way_<id>",
  "type": "way",
  "name": "display name",
  "properties": {
    "area_from": "Source Area Name",
    "area_to": "Target Area Name",
    "current_state": "open",
    "description": "A heavy oak door.",
    "pass_message": "You step through the door.",
    "cost": { "energy": 1, "time": 1 },
    "hidden": false,
    "needs_open": { "enabled": false, "skill": "Athletics", "dc": 10 },
    "tags": [],
    "auto_close": false,
    "requires": "none",
    "jump_dc": 10,
    "climb_dc": 12,
    "max_size": "normal"
  }
}
```

**Key fields:**
- `current_state`: `"open"`, `"closed"`, `"locked"`, `"hidden"`
- `cost`: `{ "energy": N, "time": N }` per passage
- `needs_open`: when `"enabled": true`, requires skill check to pass
- `requires`: `"none"`, `"jump"`, `"climb"`, `"crawl"` — triggers Athletics check
- `max_size`: `"tiny"`, `"small"`, `"normal"`, `"huge"`, `"giant"`, `"titanic"`
- `auto_close`: closes after passage

---

### 2.3 Item

```json
{
  "id": "item_<name>",
  "type": "item",
  "name": "Display Name",
  "properties": {
    "actions": ["examine", "take", "use"],
    "description": "Narrative description.",
    "current_state": "normal",
    "uses": -1,
    "weight": 0.5,
    "hidden": false,
    "tags": ["readable", "flammable", "light_source", "container", "food", "drink", "weapon", "portable"],
    "action_costs": { "use": { "energy": 1, "time": 1 } },
    "skill_check": {},
    "contents": [],
    "aliases": [],
    "equip_slots": ["head"],
    "light_level": "dim",
    "damage_dice": "1d6",
    "damage_type": "slashing",
    "defense": 0,
    "heating_rate": 0.0,
    "insulation": 0.0,
    "target_temperature": 0.0,
    "temp_range": { "min": -10, "max": 50 },
    "library_id": "",
    "locked": false,
    "locked_message": "",
    "locked_with": ""
  }
}
```

**Key fields:**
- `actions`: `examine`, `take`, `drop`, `use`, `use_on`, `eat`, `drink`, `read`, `light`, `toggle`, `open`, `close`, `break`, `throw`, `equip`, `unequip`, `inspect`, `search`, `activate`
- **DEPRECATED — do not author:** `effect_target`/`effect_stat`/`effect_amount`. Legacy consumable shortcut; give food/drink an `on_eat`/`on_drink` trigger with `adjust_vital` instead (see §20.6; task-329 removes engine support).
- `current_state`: `"normal"`, `"lit"`, `"on"`, `"broken"`, `"hidden"`, `"locked"`, `"unlocked"`, `"empty"`, `"depleted"`, `"extinguished"`, `"unlit"`, `"open"`, `"closed"`, `"jammed"`, `"frozen"`, `"wet"`, `"melted"`
- `uses`: `-1` = unlimited
- `tags`: `flammable`, `light_source`, `container`, `food`, `drink`, `weapon`, `readable`, `portable`, `sharp`, `metal`, `cloth`, `glass`, `organic`, `magic`, `cursed`, `electronic`, `document`, `tool`, `key`, `poison`, `medicine`, `explosive`, `ranged`, `armor`, `shield`
- `equip_slots`: `head`, `torso`, `legs`, `feet`, `hands`, `hand_left`, `hand_right`, `back`, `accessory`, `neck`, `waist`
- `light_level`: only meaningful when `tags` includes `light_source` and `current_state` is `"lit"`/`"on"`. Values: `"pitch_black"`, `"dim"`, `"normal"`, `"bright"`, `"blinding"`, or integer
- `action_costs`: per-action cost overrides, e.g. `{ "use": { "energy": 2, "time": 1 } }`
- `contents`: list of child item IDs for containers — creates nested `in` edges
- `hidden`: `true` = invisible until found via `on_search` or similar

---

### 2.4 Character (NPC or Player)

```json
{
  "id": "player_<name>" | "<npc_name>",
  "type": "character",
  "name": "Character Name",
  "properties": {
    "personality": "...",
    "description": "First impression shown in room descriptions.",
    "base_description": "Full physical description.",
    "stats": { "STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10 },
    "vitals": {
      "HP": 99, "Max_HP": 100,
      "Hunger": 50, "Thirst": 50, "Hygiene": 70, "Energy": 80,
      "Social": 60, "Bladder": 80, "Sanity": 90, "Entertainment": 50,
      "Temperature": 34.9, "Mana": 50
    },
    "skills": { "Perception": 2, "Athletics": 0, "Stealth": 1, "Persuasion": 1, "Survival": 2, "Acrobatics": 1 },
    "traits": {},
    "tags": ["male", "female", "animal", "child"],
    "conditions": { "awake": [{ "duration": null, "source": null, "level": 0 }] },
    "equipped": {
      "head": [], "torso": [], "legs": [], "feet": [],
      "hands": [], "hand_left": [], "hand_right": [],
      "back": [], "accessory": [], "neck": [], "waist": []
    },
    "state": "awake",
    "state_timer": 0,
    "current_area": "Starting Area",
    "decay_rates": { "Hunger": 1, "Thirst": 1, "Hygiene": 1, "Energy": 1, "Social": 1, "Bladder": 1, "Sanity": 1, "Entertainment": 1 },
    "emotion": { "current": "neutral", "description": "", "intensity": 0.0 },
    "relationships": {},
    "memories": [],
    "activity": null,
    "npc_behavior": "wander",
    "npc_action_interval": 3,
    "npc_state": "idle",
    "behaviors": [],
    "simple_npc": false
  }
}
```

**Key fields:**
- `state`: `"awake"`, `"sleeping"`, `"unconscious"`, `"stunned"`, `"grappled"`, `"restrained"`, `"prone"`, `"frightened"`, `"exhausted"`, `"paralyzed"`, `"blinded"`, `"deafened"`, `"poisoned"`, `"sick"`, `"burning"`, `"wet"`, `"frozen"`, `"drenched"`, `"bleeding"`, `"dying"`, `"dead"`
- `npc_behavior`: `"wander"`, `"flee"`, `"stationary"`, `"guard"`, `"follow"`, `"hunt"` — engine accepts arbitrary strings
- `simple_npc`: `true` skips full vitals decay for background NPCs
- `tags`: determines first-impression naming — `male` → "the man", `female` → "the woman", `animal` → species name, `child` → "the child"

---

### 2.5 Logic Trigger

```json
{
  "id": "trigger_<source>_<type>_<ts>_<rand>",
  "type": "logic_trigger",
  "name": "<trigger_type> → <effect_type>",
  "properties": {
    "trigger_type": "on_examine",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "Narrative text." } }
    ],
    "target_name": "",
    "target_state": "",
    "fail_message": "",
    "success_message": ""
  }
}
```

**Key fields:**
- `trigger_type`: one of the 27 types (see Section 5) — OR a **list** of types for a multi-type trigger (task-84): `"trigger_type": ["on_eat", "on_drink"]` fires on any of them
- `conditions`: flat list or compound tree
- `conditions_logic`: `"and"` or `"or"` for flat lists
- `effects`: **preferred** format — list of `{ "type": "...", "params": {...} }`
- `effect_type` / `effect_params`: legacy single-effect format — engine reads these only if `effects` is absent
- `fail_message`: shown when conditions fail
- `success_message`: shown when conditions pass (overrides first effect's message)

---

## 3. Edge Reference

### 3.1 `connection` (Way ↔ Area)

Bidirectional. Two edges per door.

```json
{ "source": "area_<name>", "target": "way_<id>", "type": "connection", "properties": { "cardinal": "north", "direction": "north door", "visible_in_direction": "The hallway beyond, dimly lit." } }
{ "source": "way_<id>", "target": "area_<name>", "type": "connection", "properties": { "direction": "enter" } }
```

**Required:** `direction` on both edges.
**Recommended:** `cardinal` and `visible_in_direction` on the `area → way` edge.

### 3.2 `in` (Item/Character → Area or Container)

```json
{ "source": "item_<id>", "target": "area_<id>", "type": "in", "properties": {} }
```

For nested containers: `item_<container>` → `item_<content>` with `type: "in"`.
For spatial placement: `item_<id>` → `item_<surface>` with `type: "on"` / `"under"` / `"beside"` / `"behind"` / `"at"`.

### 3.3 `triggers` (Item → Logic Trigger)

```json
{ "source": "item_<id>", "target": "trigger_<id>", "type": "triggers", "properties": { "trigger_type": "on_examine", "conditions": [], "conditions_logic": "and" } }
```

The trigger system reads `effects` from edge properties first, then from the target `logic_trigger` node properties.

### 3.4 `equipped` (Item → Character)

```json
{ "source": "item_<id>", "target": "player_<name>", "type": "equipped", "properties": { "slot": "torso" } }
```

### 3.5 `carrying` (Item → Character)

```json
{ "source": "item_<id>", "target": "player_<name>", "type": "carrying", "properties": {} }
```

---

## 4. ID Conventions

| Node Type | Convention | Example |
|---|---|---|
| Area | `area_<slug>` | `area_abandoned_hunter_s_cabin` |
| Way | `way_<id>` | `way_front_door` |
| Item | `item_<name>` | `item_brass_key` |
| Character (player) | `player_<name>` | `player_Kaelen_Voss` |
| Character (NPC) | `<name>` | `Elder_Maria` |
| Logic Trigger | `trigger_<source>_<type>_<ts>_<rand>` | `trigger_item_book_on_read_1784152362907_123` |

Edges for connections are bidirectional: `area → way` and `way → area`, both `type: "connection"`.

---

## 5. Trigger Types

| Trigger | Fires When |
|---|---|
| `on_take` | Item is picked up |
| `on_drop` | Item is dropped |
| `on_examine` | Item is examined |
| `on_inspect` | Item is closely inspected |
| `on_use` | Item used on self |
| `on_use_on` | Item used on a target |
| `on_look` | Room is looked at |
| `on_search` | Player searches/fumbles in room |
| `on_tick` | Game tick passes |
| `on_eat` | Item is eaten |
| `on_drink` | Item is consumed as drink |
| `on_read` | Item is read |
| `on_light` | Item is lit / ignited |
| `on_activate` | Item is activated |
| `on_equip` | Item is equipped |
| `on_unequip` | Item is unequipped |
| `on_throw` | Item is thrown |
| `on_break` | Item breaks |
| `on_depleted` | Item uses reach zero |
| `on_toggle_on` | Item is toggled on |
| `on_toggle_off` | Item is toggled off |
| `on_open` | Item/way is opened |
| `on_close` | Item/way is closed |
| `on_state_enter` | Character enters a state |
| `on_state_exit` | Character exits a state |
| `on_auto_open` | Way auto-opens (state change) |
| `on_enter` | Character enters an area |
| `on_speech` | Speech broadcast in area |

---

## 6. Effect Reference

Format: `{ "type": "effect_name", "params": { ... } }`

### 6.1 `message`
```json
{ "type": "message", "params": { "message": "Narrative text." } }
```

### 6.2 `damage`
```json
{ "type": "damage", "params": { "amount": 10, "dice": "1d6", "damage_type": "slashing", "target": "self", "message": "You take damage!" } }
```

### 6.3 `save` (stat save with branching)
```json
{
  "type": "save",
  "params": {
    "stat": "WIS", "dc": 12, "target": "self",
    "message": "Make a WIS save!",
    "on_success": [ { "type": "message", "params": { "message": "You resist!" } } ],
    "on_fail": [ { "type": "apply_condition", "params": { "condition": "poisoned", "duration": 5, "source": "spider", "target": "self" } } ]
  }
}
```

### 6.4 `heal`
```json
{ "type": "heal", "params": { "amount": 10, "stat": "HP", "target": "self", "message": "You feel better." } }
```

### 6.5 `spawn_item`
```json
{ "type": "spawn_item", "params": { "item_id": "item_key", "area": "Living Room", "name": "Brass Key", "message": "A key appears!" } }
```

### 6.6 `give_item`
```json
{ "type": "give_item", "params": { "item_id": "item_key", "target": "self", "name": "Brass Key", "message": "You receive a key." } }
```

### 6.7 `remove_item`
```json
{ "type": "remove_item", "params": { "item_id": "item_key", "target": "self", "message": "The item vanishes." } }
```

### 6.8 `set_state`
```json
{ "type": "set_state", "params": { "node_id": "item_door", "state": "open", "target": "self", "message": "The door opens.", "success_message": "The door creaks open." } }
```

Fan-out by tag:
```json
{ "type": "set_state", "params": { "target_tag": "flammable", "state": "extinguished", "message": "All flames die." } }
```

### 6.9 `set_environment`
```json
{ "type": "set_environment", "params": { "light": 70, "temperature": 15, "area": "self", "message": "The room brightens." } }
```

Light values: `"dim"`, `"normal"`, `"bright"`, `"pitch_black"`, `"blinding"`, or integer.

### 6.10 `teleport`
```json
{ "type": "teleport", "params": { "area": "Kitchen", "target": "self", "message": "You are pulled away!" } }
```

### 6.11 `unlock_way`
```json
{ "type": "unlock_way", "params": { "way_id": "way_front_door", "message": "The door unlocks." } }
```

`way_id` can be `"target"` to resolve from the current trigger target.

### 6.12 `adjust_vital`
```json
{ "type": "adjust_vital", "params": { "stat": "Hunger", "amount": -10, "target": "self", "message": "You are less hungry." } }
```

### 6.13 `adjust_environment`
```json
{ "type": "adjust_environment", "params": { "key": "temperature", "amount": -5, "area": "self" } }
```

### 6.14 `set_hidden`
```json
{ "type": "set_hidden", "params": { "hidden": true, "target": "item_secret_door" } }
```

### 6.15 `add_tag` / `remove_tag`
```json
{ "type": "add_tag", "params": { "tag": "light_source", "node_id": "self" } }
{ "type": "remove_tag", "params": { "tag": "flammable", "node_id": "self" } }
```

### 6.16 `set_parameter` / `adjust_parameter`
```json
{ "type": "set_parameter", "params": { "key": "uses", "value": 3, "node_id": "self" } }
{ "type": "adjust_parameter", "params": { "key": "uses", "amount": -1, "node_id": "self" } }
```

### 6.17 `adjust_uses`
```json
{ "type": "adjust_uses", "params": { "amount": -1, "target": "self" } }
```

### 6.18 `destroy_self`
```json
{ "type": "destroy_self", "params": {} }
```

### 6.19 `drain`
```json
{ "type": "drain", "params": { "stat": "Energy", "amount": 5, "duration": 3, "target": "self" } }
```

### 6.20 `consume_item`
```json
{ "type": "consume_item", "params": { "item_id": "item_apple", "target": "self" } }
```

### 6.21 `set_description` / `append_description`
```json
{ "type": "set_description", "params": { "description": "New text.", "node_id": "self" } }
{ "type": "append_description", "params": { "text": " It is now covered in frost.", "node_id": "self" } }
```

### 6.22 `rename`
```json
{ "type": "rename", "params": { "new_name": "Empty Medicine Cabinet", "node_id": "self" } }
```

### 6.23 `end_scenario` / `restart_scenario`
```json
{ "type": "end_scenario", "params": { "message": "You have survived." } }
{ "type": "restart_scenario", "params": {} }
```

### 6.24 `apply_condition`
```json
{
  "type": "apply_condition",
  "params": {
    "condition": "poisoned",
    "target": "self",
    "duration": 10,
    "source": "viper bite",
    "source_type": "item",
    "level": 0,
    "periodic": { "HP": -7 },
    "extra_conditions": [],
    "ends_on": [],
    "symptoms": {},
    "known": false
  }
}
```

### 6.25 `remove_condition`
```json
{ "type": "remove_condition", "params": { "condition": "poisoned", "target": "self" } }
```

### 6.26 `apply_trait` / `remove_trait`
```json
{ "type": "apply_trait", "params": { "trait": "hostile", "target": "self", "param": true } }
{ "type": "remove_trait", "params": { "trait": "hostile", "target": "self" } }
```

---

## 7. Conditions System

Conditions are per-character: `player.conditions[condition_id] = [instance, ...]`

### 7.1 Canonical Condition IDs

| ID | Stack | Default Duration |
|---|---|---|
| `awake` | noop | None |
| `sleeping` | noop | None |
| `unconscious` | noop | None |
| `stunned` | refresh | 1 |
| `exhausted` | refresh | 6 |
| `grappled` | noop | None |
| `restrained` | noop | None |
| `blinded` | noop | None |
| `deafened` | noop | None |
| `frightened` | accumulate | None |
| `poisoned` | accumulate | None |
| `sick` | accumulate | None |
| `burning` | accumulate | None |
| `wet` | noop | None |
| `frozen` | noop | None |
| `drenched` | noop | None |
| `bleeding` | accumulate | None |
| `dying` | noop | None |
| `dead` | noop | None |
| `prone` | noop | None |
| `paralyzed` | noop | None |

`stack`: `"accumulate"` adds instances, `"refresh"` extends/bumps level, `"noop"` ignores re-application.

### 7.2 Condition Instance

```json
{
  "duration": 10,
  "source": "spider bite",
  "source_type": "item",
  "level": 0,
  "periodic": { "HP": -7 },
  "extra_conditions": [],
  "ends_on": [],
  "symptoms": {},
  "known": false,
  "blocks_speech": false,
  "drops_held_items": false,
  "defense_mod": -5
}
```

### 7.3 Condition Context Variables

Available in condition checks: `{player_name}`, `{character_name}`, `{item_name}`, `{target_name}`, `{area_name}`, `{game_time}`, `{tick}`, `{turn_number}`, `{env}`, `{speech}`, `{target_node}`, `{item_node}`

---

## 8. Traits

Stored in `player.traits[trait_id] = value`.

| Trait ID | Value Type | Effect |
|---|---|---|
| `hostile` | boolean | NPC is hostile to player |
| `is_slasher` | boolean | Character is a slasher (combat AI) |
| `dark_vision` | boolean | Ignore light penalties |
| `immune_to_condition` | string | Immune to named condition |
| `allergic_to` | string | Take damage from tag |
| `save_on` | object | Auto-save on events |
| `action_cost_mod` | float | Multiplier on action cost |
| `vital_multiplier` | dict | `{ "Hunger": 0.5 }` |
| `vital_mod_per_tick` | dict | Per-tick vital adjustment |
| `hp_regen_multiplier` | float | HP regen multiplier |
| `energy_curve` | dict | Energy gain/loss curve |
| `group_energy_drain` | float | Drains nearby characters |
| `social_gain` | float | Social vital multiplier |
| `carry_capacity_mod` | float | Carry weight modifier |
| `move_cost_mod` | float | Movement cost modifier |
| `save_bonus` | dict | `{ "WIS": 2, "CHA": 1 }` |
| `skill_check_mod` | dict | Skill check bonuses |
| `disable_slot` | string | Disables equip slot |
| `block_sense` | string | Blocks hearing/vision |

### 8.1 `save_on` Format

```json
"save_on": { "stat": "WIS", "dc": 12, "source_type": "way", "on_success": [], "on_fail": [] }
```

---

## 9. NPC Behaviors

| Behavior | Meaning |
|---|---|
| `wander` | Move randomly between adjacent areas |
| `flee` | Run away from threats |
| `stationary` | Stay in place |
| `guard` | Stay near a specific point/character |
| `follow` | Follow a target character |
| `hunt` | Actively seek and pursue |

Engine accepts arbitrary strings — these are the canonical values observed in `world_template.json`.

---

## 10. Template Variables

Expanded in `message`, `description`, `visible_in_direction`, and similar text fields:

| Variable | Expands To |
|---|---|
| `{player_name}` | Active player name |
| `{character_name}` | Current NPC name |
| `{item_name}` | Item display name |
| `{target_name}` | Target name (for `on_use_on`) |
| `{area_name}` | Current area name |
| `{game_time}` | Current time `"HH:MM:SS"` |
| `{tick}` | Tick counter |
| `{turn_number}` | Turn counter |
| `{env}` | Environment dict serialized |
| `{speech}` | Spoken text (for `on_speech`) |

---

## 11. Common Gameplay Patterns

These are the patterns that **no AI-generated scenario got right** without explicit examples.

### 11.1 Trigger Chain: Poison Item → Condition → Drain → Cure

```json
// Item: Poisoned Apple
{
  "id": "item_poisoned_apple",
  "type": "item",
  "name": "Poisoned Apple",
  "properties": {
    "actions": ["examine", "take", "eat"],
    "description": "A red apple with a strange sheen.",
    "current_state": "normal",
    "uses": 1,
    "weight": 0.2,
    "hidden": false,
    "tags": ["food", "poison"]
  }
}

// Trigger 1: on_eat → apply_condition (poisoned, 10s, periodic HP drain)
{
  "id": "trigger_apple_eat",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_eat",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The apple tastes bitter. Your throat burns." } },
      { "type": "apply_condition", "params": {
        "condition": "poisoned",
        "target": "self",
        "duration": 10,
        "source": "poisoned apple",
        "source_type": "item",
        "level": 0,
        "periodic": { "HP": -3 },
        "known": false
      } },
      { "type": "consume_item", "params": { "item_id": "item_poisoned_apple", "target": "self" } }
    ]
  }
}

// Trigger 2: on_tick → drain HP while poisoned (on the player, or via a global tick trigger)
// This is handled automatically by the condition's `periodic` field — no separate trigger needed.

// Trigger 3: Antidote usage → remove_condition
{
  "id": "trigger_antidote_use",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_use",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The antidote burns going down. The poison fades." } },
      { "type": "remove_condition", "params": { "condition": "poisoned", "target": "self" } },
      { "type": "heal", "params": { "amount": 5, "stat": "HP", "target": "self", "message": "You feel the sickness lift." } },
      { "type": "consume_item", "params": { "item_id": "item_antidote", "target": "self" } }
    ]
  }
}
```

### 11.2 Container Items (Nested `in` Edges)

```json
// Container: Backpack
{
  "id": "item_backpack",
  "type": "item",
  "name": "Leather Backpack",
  "properties": {
    "actions": ["examine", "take", "open", "close"],
    "description": "A worn leather backpack.",
    "current_state": "open",
    "uses": -1,
    "weight": 0.5,
    "hidden": false,
    "tags": ["container", "portable"]
  }
}

// Child item: Flask
{
  "id": "item_steel_flask",
  "type": "item",
  "name": "Steel Flask",
  "properties": {
    "actions": ["examine", "take", "drink"],
    "description": "A dented steel flask.",
    "current_state": "normal",
    "uses": 3,
    "weight": 0.3,
    "hidden": false,
    "tags": ["drink", "metal"]
  }
}

// Edge: flask is IN backpack
{ "source": "item_steel_flask", "target": "item_backpack", "type": "in", "properties": {} }

// Edge: backpack is IN area
{ "source": "item_backpack", "target": "area_forest_clearing", "type": "in", "properties": {} }
```

### 11.3 Lighting Item

```json
{
  "id": "item_lantern",
  "type": "item",
  "name": "Brass Lantern",
  "properties": {
    "actions": ["examine", "take", "light", "toggle"],
    "description": "A brass lantern with a glass pane.",
    "current_state": "unlit",
    "uses": 100,
    "weight": 0.8,
    "hidden": false,
    "tags": ["light_source", "metal", "portable"]
  }
}

// Trigger: on_light → set state to lit, set environment light
{
  "id": "trigger_lantern_light",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_light",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The lantern catches. Warm light spreads." } },
      { "type": "set_state", "params": { "node_id": "item_lantern", "state": "lit", "target": "self" } },
      { "type": "set_environment", "params": { "light": "bright", "area": "self", "message": "The area is now well-lit." } }
    ]
  }
}

// Trigger: on_toggle_off → extinguish
{
  "id": "trigger_lantern_toggle_off",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_toggle_off",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The lantern goes out." } },
      { "type": "set_state", "params": { "node_id": "item_lantern", "state": "unlit", "target": "self" } },
      { "type": "set_environment", "params": { "light": "dim", "area": "self" } }
    ]
  }
}

// Trigger: on_tick → drain fuel while lit
{
  "id": "trigger_lantern_tick",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_tick",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "adjust_uses", "params": { "amount": -1, "target": "self" } }
    ]
  }
}

// Trigger: on_depleted → empty state
{
  "id": "trigger_lantern_depleted",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_depleted",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The lantern flickers and dies." } },
      { "type": "set_state", "params": { "node_id": "item_lantern", "state": "extinguished", "target": "self" } }
    ]
  }
}
```

### 11.4 Hidden Item + Search

```json
// Hidden item
{
  "id": "item_secret_key",
  "type": "item",
  "name": "Iron Key",
  "properties": {
    "actions": ["examine", "take"],
    "description": "A heavy iron key hidden under the floorboard.",
    "current_state": "hidden",
    "uses": -1,
    "weight": 0.1,
    "hidden": true,
    "tags": ["key"]
  }
}

// Trigger: on_search → reveal hidden item
{
  "id": "trigger_floorboard_search",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_search",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You pry up the loose floorboard and find an iron key hidden beneath it." } },
      { "type": "set_hidden", "params": { "hidden": false, "target": "item_secret_key" } }
    ]
  }
}
```

### 11.5 Skill Check / Save Roll

```json
// Locked chest with skill check
{
  "id": "item_iron_chest",
  "type": "item",
  "name": "Iron Chest",
  "properties": {
    "actions": ["examine", "open"],
    "description": "A heavy iron chest with a complex lock.",
    "current_state": "locked",
    "uses": -1,
    "weight": 10,
    "hidden": false,
    "tags": ["container"],
    "skill_check": { "skill": "Athletics", "dc": 12, "target": "self" }
  }
}

// Trigger: on_open → save roll with on_success/on_fail
{
  "id": "trigger_chest_open",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_open",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      {
        "type": "save",
        "params": {
          "stat": "DEX",
          "dc": 12,
          "target": "self",
          "message": "You try to pick the lock...",
          "on_success": [
            { "type": "message", "params": { "message": "The lock clicks open!" } },
            { "type": "set_state", "params": { "node_id": "item_iron_chest", "state": "open", "target": "self" } },
            { "type": "spawn_item", "params": { "item_id": "item_gold_coins", "area": "self", "name": "Gold Coins", "message": "Coins spill out!" } }
          ],
          "on_fail": [
            { "type": "message", "params": { "message": "The lock holds. Your fingers slip." } },
            { "type": "apply_condition", "params": { "condition": "stunned", "duration": 1, "source": "failed lockpick", "target": "self" } }
          ]
        }
      }
    ]
  }
}
```

### 11.6 Food / Drink

```json
// Bread
{
  "id": "item_bread",
  "type": "item",
  "name": "Loaf of Bread",
  "properties": {
    "actions": ["examine", "take", "eat"],
    "description": "A crusty loaf of bread.",
    "current_state": "normal",
    "uses": 1,
    "weight": 0.3,
    "hidden": false,
    "tags": ["food", "organic"]
  }
}

// Trigger: on_eat → adjust vital + consume
{
  "id": "trigger_bread_eat",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_eat",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You eat the bread. It's stale but filling." } },
      { "type": "adjust_vital", "params": { "stat": "Hunger", "amount": -20, "target": "self" } },
      { "type": "adjust_vital", "params": { "stat": "Energy", "amount": 5, "target": "self" } },
      { "type": "consume_item", "params": { "item_id": "item_bread", "target": "self" } }
    ]
  }
}
```

### 11.7 Area-Wide Effect via Fan-Out Targeting

```json
{
  "id": "trigger_room_enter",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_enter",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      {
        "type": "apply_condition",
        "params": {
          "condition": "wet",
          "target": "self",
          "duration": 5,
          "source": "rain",
          "source_type": "area",
          "target_by": "all_in_area",
          "target_scope": "area"
        }
      }
    ]
  }
}
```

`target_by` values: `"self"`, `"target"`, `"all_in_area"`, `"all_in_room"`, `"by_tag"`, `"by_trait"`, `"by_type"`. When `target_by` is set, the effect runs once per matching node.

### 11.8 Container Item (Nested `in` Edges)

Based on `mansion.json` container items and the nested `in` edge pattern.

```json
{
  "id": "item_jewelry_box",
  "type": "item",
  "name": "Jewelry Box",
  "properties": {
    "actions": ["examine", "take", "open", "close"],
    "description": "A small wooden jewelry box with a brass latch.",
    "current_state": "closed",
    "uses": -1,
    "weight": 0.4,
    "hidden": false,
    "tags": ["container", "portable", "furniture"]
  }
}

// Child item placed inside via nested `in` edge
{
  "id": "item_silver_ring",
  "type": "item",
  "name": "Silver Ring",
  "properties": {
    "actions": ["examine", "take"],
    "description": "A tarnished silver ring with a garnet stone.",
    "current_state": "hidden",
    "uses": -1,
    "weight": 0.05,
    "hidden": true,
    "tags": ["jewelry", "portable"]
  }
}

// Edges
{ "source": "item_jewelry_box", "target": "area_bedroom", "type": "in", "properties": {} }
{ "source": "item_silver_ring", "target": "item_jewelry_box", "type": "in", "properties": {} }

// Trigger: on_open → reveal hidden contents + message
{
  "id": "trigger_jewelry_box_open",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_open",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You lift the latch. Inside, a silver ring rests on faded velvet." } },
      { "type": "set_hidden", "params": { "hidden": false, "target": "item_silver_ring" } }
    ]
  }
}
```

**Key points:**
- `container` tag tells the engine this item can hold other items
- Contents are separate graph nodes with `in` edges pointing to the container item node
- `hidden: true` on child items keeps them invisible until revealed by a trigger
- The `contents` property on the container item is optional — the `in` edges are the source of truth

---

### 11.9 Light Source

Based on `mansion.json` flashlight (`light_level: bright`, `current_state: lit`, `uses: 60`) and `engine/lighting.py`.

```json
{
  "id": "item_lantern",
  "type": "item",
  "name": "Brass Lantern",
  "properties": {
    "actions": ["examine", "take", "light", "toggle"],
    "description": "A brass lantern with a glass pane and a wick inside.",
    "current_state": "unlit",
    "uses": 100,
    "weight": 0.8,
    "hidden": false,
    "tags": ["light_source", "metal", "portable"]
  }
}

// Trigger: on_light → ignite
{
  "id": "trigger_lantern_light",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_light",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You strike a match and light the lantern. Warm light spreads across the room." } },
      { "type": "set_state", "params": { "node_id": "item_lantern", "state": "lit", "target": "self" } },
      { "type": "set_environment", "params": { "light": "bright", "area": "self", "message": "The area is now well-lit." } }
    ]
  }
}

// Trigger: on_toggle_off → extinguish
{
  "id": "trigger_lantern_toggle_off",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_toggle_off",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You blow out the lantern. Darkness closes in." } },
      { "type": "set_state", "params": { "node_id": "item_lantern", "state": "unlit", "target": "self" } },
      { "type": "set_environment", "params": { "light": "dim", "area": "self" } }
    ]
  }
}

// Trigger: on_tick → fuel drain while lit
{
  "id": "trigger_lantern_tick",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_tick",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "adjust_uses", "params": { "amount": -1, "target": "self" } }
    ]
  }
}

// Trigger: on_depleted → empty state
{
  "id": "trigger_lantern_depleted",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_depleted",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The lantern flickers and dies." } },
      { "type": "set_state", "params": { "node_id": "item_lantern", "state": "extinguished", "target": "self" } }
    ]
  }
}
```

**Key points:**
- `light_source` tag + `light_level` + `current_state: "lit"` makes the engine include this item in light calculations (`engine/lighting.py:41-72`)
- `light_level` values: `"pitch_black"` (10), `"dim"` (30), `"normal"` (55), `"bright"` (80), `"blinding"` (95), or raw integer
- `on_light` fires when player uses the `light` action
- `on_toggle` fires for `toggle` action (on/off)
- `on_tick` drain requires a condition or `on_tick` trigger on the item — the engine does not auto-drain uses per tick
- `on_depleted` fires when `uses` reaches 0

---

### 11.10 Heat Source

Based on `heating_rate` and `target_temperature` properties used by `engine/equipment_bonuses.py`.

```json
{
  "id": "item_wood_stove",
  "type": "item",
  "name": "Wood Stove",
  "properties": {
    "actions": ["examine", "use", "light", "toggle"],
    "description": "A cast-iron wood stove, cold and dark.",
    "current_state": "unlit",
    "uses": -1,
    "weight": 50,
    "hidden": false,
    "tags": ["heat_source", "metal", "furniture"],
    "heating_rate": 15.0,
    "target_temperature": 25.0
  }
}

// Trigger: on_light → stove heats the room
{
  "id": "trigger_stove_light",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_light",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You light the stove. Soon the room begins to warm." } },
      { "type": "set_state", "params": { "node_id": "item_wood_stove", "state": "lit", "target": "self" } },
      { "type": "set_environment", "params": { "temperature": 25, "area": "self", "message": "The room grows comfortably warm." } }
    ]
  }
}

// Trigger: on_toggle_off → stove cools
{
  "id": "trigger_stove_toggle_off",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_toggle_off",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The fire dies down. The room grows cold again." } },
      { "type": "set_state", "params": { "node_id": "item_wood_stove", "state": "unlit", "target": "self" } },
      { "type": "set_environment", "params": { "temperature": 12, "area": "self" } }
    ]
  }
}
```

**Key points:**
- `heating_rate` — float, degrees per tick the stove adds to the area's ambient temperature
- `target_temperature` — the equilibrium temperature the stove tries to reach
- Used by `engine/equipment_bonuses.py` `effective_temperature()` when a character is near the heat source
- The actual `set_environment` trigger is what changes the displayed temperature — `heating_rate`/`target_temperature` are passive modifiers the engine reads when calculating `feels_like` temperature
- `temp_range` on the item itself limits the temperatures it can survive (e.g., `{ "min": -20, "max": 200 }`)

---

### 11.11 Clothing with Insulation

Based on `mansion.json`: field jacket (`insulation: 5`, `defense: 3`), dark cargo pants (`insulation: 4`, `defense: 3`), sneakers (`insulation: 2`, `defense: 2`).

```json
{
  "id": "item_field_jacket",
  "type": "item",
  "name": "Field Jacket",
  "properties": {
    "actions": ["examine", "take", "equip", "unequip"],
    "description": "A heavy canvas field jacket with a liner. Worn but serviceable.",
    "current_state": "normal",
    "uses": -1,
    "weight": 1.2,
    "hidden": false,
    "tags": ["clothing", "outerwear", "insulation"],
    "equip_slots": ["torso"],
    "insulation": 5,
    "defense": 3
  }
}

{
  "id": "item_wool_sweater",
  "type": "item",
  "name": "Wool Sweater",
  "properties": {
    "actions": ["examine", "take", "equip", "unequip"],
    "description": "A thick wool sweater, slightly itchy but very warm.",
    "current_state": "normal",
    "uses": -1,
    "weight": 0.6,
    "hidden": false,
    "tags": ["clothing", "top", "insulation"],
    "equip_slots": ["torso"],
    "insulation": 3,
    "defense": 1
  }
}

// Trigger: on_equip → apply insulation trait
{
  "id": "trigger_jacket_equip",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_equip",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You put on the jacket. It's heavy but the cold stops at your skin." } },
      { "type": "apply_trait", "params": { "trait": "insulated", "target": "self", "param": 5 } }
    ]
  }
}

// Trigger: on_unequip → remove trait
{
  "id": "trigger_jacket_unequip",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_unequip",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You take off the jacket. The cold seeps in immediately." } },
      { "type": "remove_trait", "params": { "trait": "insulated", "target": "self" } }
    ]
  }
}
```

**Key points:**
- `insulation` — integer, reduces cold damage / improves effective temperature. Higher = warmer.
- `defense` — integer, reduces incoming physical damage when equipped. Same field used by armor.
- Both are read by `engine/equipment_bonuses.py` when the item has an `equipped` edge to the character
- `equip_slots` must match the character's `equipped` dict slots for the edge to be valid
- The `insulated` trait in the example above would need to be defined in the trait system or applied via `apply_trait` with a custom param — currently `insulation` is a raw item property, not a trait

---

### 11.12 Weapon

Based on `damage_dice`, `damage_type`, `defense` properties from `mansion.json` and `engine/combat.py`.

```json
{
  "id": "item_rusty_hatchet",
  "type": "item",
  "name": "Rusty Hatchet",
  "properties": {
    "actions": ["examine", "take", "equip", "unequip", "throw", "attack"],
    "description": "A rusted hatchet with a worn wooden handle.",
    "current_state": "normal",
    "uses": -1,
    "weight": 1.5,
    "hidden": false,
    "tags": ["weapon", "sharp", "metal", "portable"],
    "equip_slots": ["hand_right", "hand_left"],
    "damage_dice": "1d6",
    "damage_type": "slashing",
    "defense": 0
  }
}

{
  "id": "item_wooden_shield",
  "type": "item",
  "name": "Wooden Shield",
  "properties": {
    "actions": ["examine", "take", "equip", "unequip"],
    "description": "A battered wooden shield with iron banding.",
    "current_state": "normal",
    "uses": -1,
    "weight": 3.0,
    "hidden": false,
    "tags": ["armor", "shield", "wood"],
    "equip_slots": ["hand_left", "hand_right"],
    "damage_dice": "1d3",
    "damage_type": "bludgeoning",
    "defense": 4
  }
}

// Trigger: on_equip → message
{
  "id": "trigger_hatchet_equip",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_equip",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You grip the hatchet. It's unbalanced but the edge is still sharp." } }
    ]
  }
}
```

**Key points:**
- `damage_dice` — dice notation string: `"1d4"`, `"2d6"`, `"1d8+2"`, etc. Used by `engine/combat.py`
- `damage_type` — `"slashing"`, `"piercing"`, `"bludgeoning"`, `"fire"`, `"cold"`, `"lightning"`, `"poison"`, `"radiant"`, `"necrotic"`, `"force"`
- `defense` — integer, added to the wielder's defense when equipped. Shields typically 3–5, armor 2–8
- Combat formula: `attack + attack_mod - target_defense_mod` (`engine/combat.py:158-172`)
- `is_slasher` trait gives bonus to slashing attacks
- Weapons need `equip_slots` and `equipped` edges to function in combat

---

### 11.13 Abilities (Traits as Powers)

Based on `TRAIT_DEFINITIONS` in `engine/traits.py` — abilities are traits applied via `apply_trait` effect or placed on character creation.

```json
// Character with innate abilities
{
  "id": "player_Violet_Parr",
  "type": "character",
  "name": "Violet Parr",
  "properties": {
    "stats": { "STR": 8, "DEX": 16, "CON": 10, "INT": 16, "WIS": 13, "CHA": 14 },
    "vitals": { "HP": 100, "Max_HP": 100, "Mana": 100, ... },
    "skills": { "Stealth": 3, "Persuasion": 2, ... },
    "traits": {
      "dark_vision": true,
      "invisibility": true,
      "forcefield": { "duration": 3, "uses": 5 }
    },
    "state": "awake",
    ...
  }
}

// Ability trigger: invisibility activation
{
  "id": "trigger_violet_invisibility_activate",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_activate",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You focus. The world blurs at the edges and you feel yourself slipping out of sight." } },
      { "type": "apply_condition", "params": {
        "condition": "invisible",
        "target": "self",
        "duration": 5,
        "source": "invisibility power",
        "source_type": "trait",
        "level": 0,
        "known": true
      } },
      { "type": "adjust_parameter", "params": { "key": "Mana", "amount": -20, "node_id": "player_Violet_Parr" } }
    ]
  }
}
```

**Key points:**
- Abilities are traits on the character — `dark_vision`, `is_slasher`, `hostile`, `save_on` traits, etc.
- `TRAIT_DEFINITIONS` in `engine/traits.py` is the canonical catalog; custom trait IDs are accepted but won't have engine behavior unless they match known effect keys
- `save_on` traits fire automatically on world events (`enter_area`, `climb_way`, `see_item`, `takes_damage`, `alone_in_dark`, etc.)
- `grants_conditions` traits auto-apply conditions when the trait is applied: `"chronically_ill"` grants `sick` with `periodic: {Hunger: -1, Thirst: -1}`
- `behavior_prompt` on traits gives the LLM agent narrative guidance for NPCs with that trait

**Canonical ability traits from `engine/traits.py`:**

| Trait | Effect |
|---|---|
| `dark_vision` | See in complete darkness |
| `is_slasher` | Horror monster — exempt from vital decay, dark vision, combat AI |
| `hostile` | Threat marker — NPCs flee/fight |
| `immune_to_condition: "poisoned"` | Cannot be poisoned |
| `allergic_to: "pollen"` | Takes damage when near `pollen`-tagged items |
| `chronically_ill` | Grants `sick` condition with periodic Hunger/Thirst drain |
| `paranoid` | Grants `frightened` condition + behavior prompt |
| `claustrophobic` | `save_on` → WIS save on `crawl_tight_way` |
| `acrophobic` | `save_on` → WIS save on `climb_way`/`jump_way` |
| `hemophobic` | `save_on` → WIS save on `see_item` with blood/corpse tags |
| `cowardly` | `save_on` → WIS save on `takes_damage` |
| `iron_will` | `+2 WIS saves` via `save_bonus` |
| `sharp_eyed` | `+2 Perception` via `skill_check_mod` |
| `strong_backed` | `2x carry capacity` via `carry_capacity_mod` |
| `sprinter` | `-1 energy per movement` via `move_cost_mod` |

---

### 11.14 Spells (Magic Items with Activation)

Spells are items with the `magic` tag and `on_activate`/`on_use` triggers that consume Mana or have limited `uses`.

```json
{
  "id": "item_spell_scroll_fireball",
  "type": "item",
  "name": "Spell Scroll: Fireball",
  "properties": {
    "actions": ["examine", "take", "read", "activate"],
    "description": "A parchment scroll inscribed with fiery runes. The words shift and dance before your eyes.",
    "current_state": "normal",
    "uses": 1,
    "weight": 0.05,
    "hidden": false,
    "tags": ["magic", "readable", "document", "portable"]
  }
}

// Trigger: on_read → learn spell (spawn a spell item)
{
  "id": "trigger_scroll_read",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_read",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "The scroll dissolves in your hands. The magic flows into your mind — you now know Fireball." } },
      { "type": "spawn_item", "params": { "item_id": "item_spell_fireball_learned", "target": "self", "name": "Fireball Spell", "message": "You gained the Fireball spell!" } },
      { "type": "consume_item", "params": { "item_id": "item_spell_scroll_fireball", "target": "self" } }
    ]
  }
}

// The learned spell as a reusable item
{
  "id": "item_spell_fireball_learned",
  "type": "item",
  "name": "Fireball",
  "properties": {
    "actions": ["examine", "activate"],
    "description": "A spell known to you. You can cast it by concentrating.",
    "current_state": "normal",
    "uses": 3,
    "weight": 0,
    "hidden": false,
    "tags": ["magic"]
  }
}

// Trigger: on_activate → cast fireball (damage + condition)
{
  "id": "trigger_fireball_cast",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_activate",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You thrust your hands forward. A sphere of searing flame erupts, lighting the room." } },
      { "type": "damage", "params": { "amount": 20, "dice": "4d6", "damage_type": "fire", "target": "target", "message": "The fireball hits for {amount} fire damage!" } },
      { "type": "adjust_parameter", "params": { "key": "uses", "amount": -1, "node_id": "item_spell_fireball_learned" } },
      { "type": "adjust_vital", "params": { "stat": "Mana", "amount": -15, "target": "self" } }
    ]
  }
}
```

**Key points:**
- `magic` tag enables Mana usage (Mana vital is conditional on this tag)
- Spells consume Mana per cast via `adjust_vital: {stat: "Mana"}`
- `on_activate` is the canonical spell-cast trigger
- `on_read` is for learning from scrolls (consumes the scroll, spawns a reusable spell item)
- `target` in damage effects resolves from `target_name` on `on_use_on` or defaults to `self` for `on_activate`
- The `spell` concept isn't a separate node type — it's an item with `magic` tag and activation triggers

---

### 11.15 Disease (Contagious Condition)

Based on `sick`/`poisoned` condition definitions in `player.py`, `grants_conditions` traits in `engine/traits.py`, and the `apply_condition` effect with `periodic` drains.

```json
// Contagious disease item (infected blood)
{
  "id": "item_blood_sample",
  "type": "item",
  "name": "Blood Sample",
  "properties": {
    "actions": ["examine", "take"],
    "description": "A vial of blood. It looks... wrong. The liquid moves slightly against gravity.",
    "current_state": "normal",
    "uses": -1,
    "weight": 0.1,
    "hidden": false,
    "tags": ["medical", "organic", "contagious"]
  }
}

// Trigger: on_take → exposure risk (CON save or contract disease)
{
  "id": "trigger_blood_exposure",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_take",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      {
        "type": "save",
        "params": {
          "stat": "CON",
          "dc": 13,
          "target": "self",
          "message": "You handle the blood. Something in it feels alive.",
          "on_success": [
            { "type": "message", "params": { "message": "Your system fights it off. You feel a chill but it passes." } }
          ],
          "on_fail": [
            { "type": "message", "params": { "message": "A hot flush spreads through you. You're infected." } },
            { "type": "apply_condition", "params": {
              "condition": "sick",
              "target": "self",
              "duration": 30,
              "source": "blood sample",
              "source_type": "item",
              "level": 1,
              "periodic": { "HP": -2, "Hunger": -3, "Thirst": -2 },
              "known": false
            } }
          ]
        }
      }
    ]
  }
}

// Disease progression: on_tick → worsening symptoms
{
  "id": "trigger_disease_progression",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_tick",
    "conditions": [
      { "type": "has_condition", "value": "sick" }
    ],
    "conditions_logic": "and",
    "effects": [
      { "type": "adjust_vital", "params": { "stat": "Sanity", "amount": -1, "target": "self" } },
      { "type": "message", "params": { "message": "Your skin burns. The world swims at the edges." } }
    ]
  }
}

// Contagion: on_speech → spread to nearby characters
{
  "id": "trigger_disease_speech",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_speech",
    "conditions": [
      { "type": "has_condition", "value": "sick" }
    ],
    "conditions_logic": "and",
    "effects": [
      {
        "type": "apply_condition",
        "params": {
          "condition": "sick",
          "target": "self",
          "duration": 20,
          "source": "airborne pathogen",
          "source_type": "area",
          "level": 0,
          "periodic": { "HP": -1 },
          "target_by": "all_in_area",
          "target_scope": "area"
        }
      }
    ]
  }
}

// Cure: antidote removes sick condition
{
  "id": "trigger_antidote_cure",
  "type": "logic_trigger",
  "properties": {
    "trigger_type": "on_use",
    "conditions": [],
    "conditions_logic": "and",
    "effects": [
      { "type": "message", "params": { "message": "You drink the antidote. The fever breaks within minutes." } },
      { "type": "remove_condition", "params": { "condition": "sick", "target": "self" } },
      { "type": "heal", "params": { "amount": 10, "stat": "HP", "target": "self" } },
      { "type": "consume_item", "params": { "item_id": "item_antidote", "target": "self" } }
    ]
  }
}
```

**Key points:**
- `sick` condition has `stack: "accumulate"` — multiple exposures stack instances, drains sum
- `periodic: {"HP": -2, "Hunger": -3}` runs every tick while the condition is active (`engine/conditions.py:69-71`)
- `source_type: "area"` + `target_by: "all_in_area"` makes the disease area-contagious
- `source_type: "item"` + `target: "self"` on `on_take` makes it exposure-based
- `save_on` trait can give automatic saves: `"hemophobic"` saves on `see_item` with blood tags — a similar pattern works for disease exposure
- `immune_to_condition: "sick"` trait makes a character completely immune
- `chronically_ill` trait grants `sick` permanently via `grants_conditions` with periodic drain
- Disease progression uses `on_tick` with `has_condition` gate to worsen symptoms over time

**Summary of what each special item type needs:**

| Type | Critical properties | Critical triggers | Critical edges |
|---|---|---|---|
| Container | `tags: ["container"]`, `actions: ["open","close"]` | `on_open` (reveal), `on_close` | `in` edges from children to container |
| Light source | `tags: ["light_source"]`, `light_level`, `current_state` | `on_light`, `on_toggle_off`, `on_tick`, `on_depleted` | `in` to area |
| Heat source | `heating_rate`, `target_temperature`, `temp_range` | `on_light`, `on_toggle_off`, `on_tick` | `in` to area |
| Clothing | `insulation`, `defense`, `equip_slots`, `tags: ["clothing"]` | `on_equip` (apply trait), `on_unequip` (remove trait) | `equipped` edge to character |
| Weapon | `damage_dice`, `damage_type`, `defense`, `equip_slots` | `on_equip`, `on_unequip` | `equipped` edge to character |
| Ability | Trait on character (`traits` dict) | `on_activate` for active abilities; `save_on` for reactive | `equipped`/`in` as appropriate |
| Spell | `tags: ["magic"]`, `on_activate` trigger, Mana drain | `on_activate` (cast), `on_read` (learn) | `in` to area or `carrying` to character |
| Disease | `apply_condition` with `periodic`, `source_type` | `on_take` (exposure), `on_tick` (progression), `on_speech` (contagion) | `in` to area; `target_by: "all_in_area"` for spread |

---

## 12. Compound Conditions

Flat list with `conditions_logic`:
```json
{ "conditions": [{ "type": "has_tag", "value": "key" }], "conditions_logic": "and" }
```

Compound tree:
```json
{
  "operator": "and",
  "conditions": [
    { "type": "has_item", "value": "item_key" },
    {
      "operator": "or",
      "conditions": [
        { "type": "state_is", "value": "awake" },
        { "type": "has_trait", "value": "dark_vision" }
      ]
    }
  ]
}
```

Operators: `"and"`, `"or"`, `"not"`. `"not"` takes a single condition or a nested tree.

---

## 13. Character Memories Format

**Always use dicts, never bare strings.**

```json
"memories": [
  {
    "id": "mem_1785853798512_563",
    "text": "The valerius case - who are they, where are they?",
    "importance": 5,
    "source": "auto",
    "tags": ["investigation"],
    "location": "Blizzard Forest Clearing",
    "entity_ids": ["player_Violet_Parr"]
  }
]
```

Required keys: `id`, `text`. Optional: `importance` (1–5), `source`, `tags`, `location`, `entity_ids`, `embedding`.

---

## 14. What To Never Do

1. **Don't put data only in denormalized blocks.** `areas`, `ways`, `players`, `rooms` are written by `to_dict()` but never read by `load_from_dict()`. The engine reads `graph.nodes` and `graph.edges` only.
2. **Don't use bare strings for memories.** Always `{ "id", "text", ... }`.
3. **Don't invent new fields.** There is no `inventory` field on characters. There is no `world_name` top-level key.
4. **Don't leave `connection` edges empty.** Always include `direction` at minimum; `cardinal` and `visible_in_direction` are required for navigation to work.
5. **Don't forget `equipped`/`carrying` edges.** The `equipped` dict on a character is a view. The actual edges are what the engine queries.
6. **Don't use the `effects` single-effect format** (`effect_type`/`effect_params`) when the `effects` list format is available.
7. **Don't leave `condition` fields as flat strings.** Use `{ "type": "...", "value": "..." }` dicts, or put them in a `conditions` list.
8. **Don't omit `target_name` on `on_use_on` triggers.** The engine can't resolve the target without it.
9. **Don't use `player_` prefix on NPC IDs.** Only the active player uses `player_<name>`. NPCs use bare names.
10. **Don't put `cardinal` on the way node.** It goes on the `connection` edge properties.

---

## 15. Common Failure Modes (Observed in AI Output)

| Failure | Model | Symptom |
|---|---|---|
| Memories as `["string"]` | ChatGPT | Engine crash: `'str' object has no attribute 'get'` |
| Data only in `areas`/`players` blocks | Gemini | World loads but is empty — no items, no chars, no triggers at runtime |
| Custom top-level schema | Qwen, DS JSON | File won't load at all |
| Empty `connection` edge properties | ChatGPT | Navigation works but no direction names shown |
| No `equipped`/`carrying` edges | All models | Inventory system unused |
| Single-step triggers only | All models | No gameplay chains — just "examine → message" |
| No `on_use_on` / `use_on` action | All models | Can't use items on targets |
| `inventory` field invented | ChatGPT | Harmless but non-canonical |
| `effect_type`/`effect_params` instead of `effects` | World template | Works but is legacy — `effects` list is preferred |
| Flat conditions only | All models | No OR/NOT logic |
| No `fail_message` / `on_fail` | All models | No failure states |
| No `target_by` fan-out | All models | No area-wide effects |

---

## 16. Minimum Viable Checklists

### 16.1 Complete Area
- [ ] `id`: `area_<slug>`
- [ ] `name`: display name
- [ ] `description`: narrative text
- [ ] `environment`: all 5 keys (`light`, `temperature`, `air`, `smell`, `noise`)
- [ ] `tags`: at least 1

### 16.2 Complete Way
- [ ] `id`: `way_<id>`
- [ ] `area_from` / `area_to`: exact area names
- [ ] `current_state`: open/closed/locked/hidden
- [ ] `description`: narrative text
- [ ] `cost`: `{ "energy": N, "time": N }` or `{}`
- [ ] Bidirectional `connection` edges with `cardinal` + `direction`

### 16.3 Complete Interactive Item
- [ ] `id`: `item_<name>`
- [ ] `actions`: includes at least `examine` + one interaction action
- [ ] `uses`: `-1` or finite
- [ ] `current_state`: non-hidden state
- [ ] `hidden`: boolean
- [ ] `tags`: semantic tags (`key`, `food`, `light_source`, `container`, etc.)
- [ ] At least 1 `triggers` edge with a `logic_trigger` node
- [ ] `in` edge to an area or container

### 16.4 Complete Character
- [ ] `id`: `player_<name>` (player) or `<name>` (NPC)
- [ ] `stats`: all 6 keys
- [ ] `vitals`: all 12 keys
- [ ] `skills`: at least 3 keys
- [ ] `state`: canonical value
- [ ] `equipped`: all 11 slot keys (even if empty)
- [ ] `npc_behavior`: canonical value
- [ ] `memories`: list of `{id, text, ...}` dicts, not strings
- [ ] `conditions`: at least `awake` instance
- [ ] `decay_rates`: at least 3 keys
- [ ] `emotion`: `{current, description, intensity}`
- [ ] `in` edge to current area
- [ ] **wardrobe**: every item the description claims they're wearing exists as an item node + `equipped` edge — the `equipped` dict in `players` is a VIEW; a character with no clothing edges spawns naked no matter what the description says

### 16.5 Complete Trigger
- [ ] `trigger_type`: one of the 27 types
- [ ] `conditions`: list or tree (can be empty `[]`)
- [ ] `conditions_logic`: `"and"` or `"or"`
- [ ] `effects`: list of `{type, params}` — at least 1
- [ ] For `on_use_on`: `target_name` set
- [ ] For gated triggers: `fail_message` present

---

## 17. Complete Minimal Example (With Trigger Chain)

```json
{
  "active_player": "Adventurer",
  "clock_start_hour": 8,
  "clock_start_minute": 0,
  "current_area": "Forest Clearing",
  "game_time": "08:00:00",
  "ghost_mode": false,
  "narration_mode": "none",
  "time_per_tick_minutes": 5,
  "time_ticks": 0,
  "turn_number": 0,
  "graph": {
    "nodes": {
      "area_forest_clearing": {
        "id": "area_forest_clearing",
        "type": "area",
        "name": "Forest Clearing",
        "properties": {
          "description": "A quiet forest clearing. Sunlight filters through the canopy.",
          "environment": { "light": "normal", "temperature": 18, "air": "fresh", "smell": "pine", "noise": "birdsong" },
          "floor": 0,
          "tags": ["exterior"]
        }
      },
      "area_cabin": {
        "id": "area_cabin",
        "type": "area",
        "name": "Rustic Cabin",
        "properties": {
          "description": "A small cabin with a cold hearth.",
          "environment": { "light": "dim", "temperature": 12, "air": "stale", "smell": "dust", "noise": "silence" },
          "floor": 0
        }
      },
      "way_cabin_door": {
        "id": "way_cabin_door",
        "type": "way",
        "name": "cabin door",
        "properties": {
          "area_from": "Forest Clearing",
          "area_to": "Rustic Cabin",
          "current_state": "closed",
          "description": "A heavy wooden door.",
          "pass_message": "You push open the door.",
          "cost": { "energy": 1, "time": 1 },
          "hidden": false
        }
      },
      "item_lantern": {
        "id": "item_lantern",
        "type": "item",
        "name": "Brass Lantern",
        "properties": {
          "actions": ["examine", "take", "light", "toggle"],
          "description": "A brass lantern with a glass pane.",
          "current_state": "unlit",
          "uses": 100,
          "weight": 0.8,
          "hidden": false,
          "tags": ["light_source", "metal", "portable"]
        }
      },
      "item_poisoned_apple": {
        "id": "item_poisoned_apple",
        "type": "item",
        "name": "Poisoned Apple",
        "properties": {
          "actions": ["examine", "take", "eat"],
          "description": "A red apple with a strange sheen.",
          "current_state": "normal",
          "uses": 1,
          "weight": 0.2,
          "hidden": false,
          "tags": ["food", "poison"]
        }
      },
      "item_antidote": {
        "id": "item_antidote",
        "type": "item",
        "name": "Antidote Vial",
        "properties": {
          "actions": ["examine", "take", "use"],
          "description": "A small glass vial with a green liquid.",
          "current_state": "normal",
          "uses": 1,
          "weight": 0.1,
          "hidden": false,
          "tags": ["medicine", "glass"]
        }
      },
      "player_Adventurer": {
        "id": "player_Adventurer",
        "type": "character",
        "name": "Adventurer",
        "properties": {
          "stats": { "STR": 12, "DEX": 14, "CON": 12, "INT": 10, "WIS": 10, "CHA": 8 },
          "vitals": { "HP": 50, "Max_HP": 50, "Hunger": 60, "Thirst": 60, "Hygiene": 80, "Energy": 90, "Social": 50, "Bladder": 70, "Sanity": 100, "Entertainment": 40, "Temperature": 21, "Mana": 0 },
          "skills": { "Perception": 2, "Athletics": 1, "Stealth": 0, "Persuasion": 0, "Survival": 1, "Acrobatics": 1 },
          "state": "awake",
          "current_area": "Forest Clearing",
          "decay_rates": { "Hunger": 1, "Thirst": 1, "Hygiene": 1, "Energy": 1, "Social": 1, "Bladder": 1, "Sanity": 1, "Entertainment": 1 },
          "equipped": { "head": [], "torso": [], "legs": [], "feet": [], "hands": [], "back": [], "accessory": [], "neck": [], "waist": [] },
          "npc_behavior": "wander",
          "npc_action_interval": 3,
          "npc_state": "idle",
          "behaviors": [],
          "simple_npc": false
        }
      },
      "trigger_lantern_light": {
        "id": "trigger_lantern_light",
        "type": "logic_trigger",
        "name": "on_light → set_state + set_environment",
        "properties": {
          "trigger_type": "on_light",
          "conditions": [],
          "conditions_logic": "and",
          "effects": [
            { "type": "message", "params": { "message": "The lantern catches. Warm light spreads." } },
            { "type": "set_state", "params": { "node_id": "item_lantern", "state": "lit", "target": "self" } },
            { "type": "set_environment", "params": { "light": "bright", "area": "self", "message": "The area is now well-lit." } }
          ]
        }
      },
      "trigger_apple_eat": {
        "id": "trigger_apple_eat",
        "type": "logic_trigger",
        "name": "on_eat → apply_condition + consume",
        "properties": {
          "trigger_type": "on_eat",
          "conditions": [],
          "conditions_logic": "and",
          "effects": [
            { "type": "message", "params": { "message": "The apple tastes bitter. Your throat burns." } },
            { "type": "apply_condition", "params": {
              "condition": "poisoned", "target": "self", "duration": 10,
              "source": "poisoned apple", "source_type": "item", "level": 0,
              "periodic": { "HP": -3 }, "known": false
            } },
            { "type": "consume_item", "params": { "item_id": "item_poisoned_apple", "target": "self" } }
          ]
        }
      },
      "trigger_antidote_use": {
        "id": "trigger_antidote_use",
        "type": "logic_trigger",
        "name": "on_use → remove_condition + heal",
        "properties": {
          "trigger_type": "on_use",
          "conditions": [],
          "conditions_logic": "and",
          "effects": [
            { "type": "message", "params": { "message": "The antidote burns going down. The poison fades." } },
            { "type": "remove_condition", "params": { "condition": "poisoned", "target": "self" } },
            { "type": "heal", "params": { "amount": 5, "stat": "HP", "target": "self", "message": "You feel the sickness lift." } },
            { "type": "consume_item", "params": { "item_id": "item_antidote", "target": "self" } }
          ]
        }
      }
    },
    "edges": [
      { "source": "area_forest_clearing", "target": "way_cabin_door", "type": "connection", "properties": { "cardinal": "north", "direction": "cabin door", "visible_in_direction": "A rustic cabin stands among the trees." } },
      { "source": "way_cabin_door", "target": "area_cabin", "type": "connection", "properties": { "direction": "enter" } },
      { "source": "way_cabin_door", "target": "area_forest_clearing", "type": "connection", "properties": { "direction": "cabin door" } },
      { "source": "area_cabin", "target": "way_cabin_door", "type": "connection", "properties": { "cardinal": "south", "direction": "cabin door", "visible_in_direction": "The forest clearing is sunny and green." } },
      { "source": "item_lantern", "target": "area_forest_clearing", "type": "in", "properties": {} },
      { "source": "item_poisoned_apple", "target": "area_forest_clearing", "type": "in", "properties": {} },
      { "source": "item_antidote", "target": "area_cabin", "type": "in", "properties": {} },
      { "source": "player_Adventurer", "target": "area_forest_clearing", "type": "in", "properties": {} },
      { "source": "item_lantern", "target": "trigger_lantern_light", "type": "triggers", "properties": { "trigger_type": "on_light" } },
      { "source": "item_poisoned_apple", "target": "trigger_apple_eat", "type": "triggers", "properties": { "trigger_type": "on_eat" } },
      { "source": "item_antidote", "target": "trigger_antidote_use", "type": "triggers", "properties": { "trigger_type": "on_use" } }
    ]
  }
}
```

---

## 18. Denormalized Blocks (Reference Only)

Written by `to_dict()` for convenience. `areas` / `rooms` / `ways` / `item_registry` /
`players_in_area` are **not read on load** — but `players`, `world_lore`, and the time/
turn settings ARE (see §1).

### 18.1 `areas` / `rooms`

```json
{
  "Area Name": {
    "name": "Area Name",
    "description": "...",
    "environment": { "light": "normal", "temperature": 21, "air": "fresh", "smell": "neutral", "noise": "quiet" },
    "exits": { "north": { "target": "Other Area", "state": "open", "description": "...", "hidden": false, "pass_message": "", "return_dir": "south", "visible_in_direction": "", "cost": {}, "cardinal": "north", "way_id": "way_..." } },
    "items": [],
    "floor": 0,
    "light_description": "normal",
    "properties": { "description": "...", "environment": {...}, "tags": [] }
  }
}
```

### 18.2 `ways`

```json
{
  "way_id": {
    "display_name": "door name",
    "area_from": "Area A",
    "area_to": "Area B",
    "current_state": "open",
    "description": "...",
    "cost": {},
    "hidden": false,
    "needs_open": { "enabled": false, "skill": "Athletics", "dc": 10 },
    "direction": "north",
    "cardinal": "north",
    "pass_message": "",
    "return_dir": "south",
    "visible_in_direction": "",
    "tags": [],
    "requires": "none",
    "jump_dc": 10,
    "climb_dc": 12,
    "max_size": "normal"
  }
}
```

### 18.3 `players`

```json
{
  "PlayerName": {
    "name": "PlayerName",
    "personality": "...",
    "description": "...",
    "base_description": "...",
    "stats": { "STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10 },
    "vitals": { "HP": 99, "Max_HP": 100, "Hunger": 50, "Thirst": 50, ... },
    "skills": { "Perception": 2, "Athletics": 0, ... },
    "traits": {},
    "tags": [],
    "interest_tags": [],
    "equipped": { "head": [], "torso": [], ... },
    "state": "awake",
    "conditions": {},
    "current_area": "Starting Area",
    "decay_rates": { "Hunger": 1, "Thirst": 1, ... },
    "emotion": { "current": "neutral", "description": "", "intensity": 0.0 },
    "relationships": {},
    "memories": [],
    "activity": null,
    "simple_npc": false,
    "npc_behavior": "wander",
    "npc_action_interval": 3,
    "npc_state": "idle",
    "behaviors": [],
    "feels_like": 2,
    "recent_hearing": []
  }
}
```

### 18.4 `item_registry`

Dict of library item blueprints. Informational — placed items live in the graph.

### 18.5 `world_lore`

List of `{ "id", "category", "title", "content" }` entries.

---

## 19. Tips for LLM Prompting

1. **Always produce `graph.nodes` + `graph.edges`** — they are the source of truth. Denormalized blocks are optional.
2. **Item IDs**: prefix with `item_`, way IDs with `way_`, areas with `area_`.
3. **Bidirectional connections**: every way needs two `connection` edges with `cardinal` + `direction`.
4. **Place items via `in` edges** pointing to `area_<slug>` or `item_<container>`.
5. **Use `effects` list format** on logic_trigger nodes and trigger edges.
6. **Keep conditions as flat lists** for AND logic; use compound trees for OR/NOT.
7. **Template variables**: use `{player_name}`, `{game_time}`, etc. in narrative strings.
8. **Player vitals**: always include all 12 vitals when creating a player character.
9. **Way states**: `hidden` doors use `current_state: "hidden"` plus `hidden: true`.
10. **Tags**: use standard tags (`flammable`, `light_source`, `container`, `food`, `drink`, `weapon`, `readable`, `portable`, `key`) so item actions resolve correctly.
11. **Item actions**: `use_on` requires `target_name`; `use` does not.
12. **NPC memory**: `memories` is a list of `{ "id", "text", "importance", "source", "tags", "location", "entity_ids" }` — **never bare strings**.
13. **Equipment**: always create `equipped`/`carrying` edges for items a character holds or wears.
14. **Triggers**: every interactive item should have at least one trigger. A bare `on_examine → message` is fine for flavor, but interactive items need `on_use`/`on_eat`/`on_take` etc.
15. **Chaining**: use multi-effect lists to create cause-and-effect chains: `on_take → apply_condition`, `on_eat → adjust_vital + consume_item`, `on_use → heal + remove_condition`.
16. **NPC behaviors**: valid values include `wander`, `flee`, `stationary`, `guard`, `follow`, `hunt`.
17. **Connection edges**: `cardinal` and `visible_in_direction` go on the `connection` edge, not the way node.
18. **Don't invent fields**: there is no `inventory`, `world_name`, or `connections` list.

---

## 20. Playtest Gotchas (2026-08-23)

Learned by authoring and running scenarios end-to-end (taco_bell_date; multi-agent
mansion runs).

### 20.1 `active_player` is NOT the human player

It's the initiative/turn cursor — whoever acts next. Human control of a character comes
from `"autonomy": false` on that character's entry in `players`. Setting `active_player`
does not make anyone player-controlled.

### 20.2 Characters hydrate from `players`, not graph nodes

Graph `character` nodes are bare anchors (the loader creates them empty if missing).
Personality, descriptions, stats, vitals, skills, traits, memories, emotion,
`npc_behavior`, and `autonomy` all come from the `players` block. A character that only
exists as a graph node does not exist as a being.

### 20.3 World lore needs `title`

Prompts render `[category] title: content`; an entry without `title` shows a literal
`undefined:` in every agent prompt. Shape: `{ "category", "title", "content" }`.

### 20.4 Item concealment = `current_state: "hidden"`

Every visibility filter checks `properties.current_state == "hidden"`
(`area_description.py:107`, `matching.py`, `narration.py`). The boolean
`hidden: true` property alone conceals nothing. The `set_hidden` effect flips
`current_state`. For search-gated items set `current_state: "hidden"` (boolean too, for
clarity), place with an explicit spatial edge (`under`/`on`/…), and reveal via
`on_search` → `set_hidden false`.

### 20.5 Second-person conversion hazard

Character descriptions are rewritten third→second person for agent prompts ("his eyes" →
"your eyes"). Pronoun+verb constructions convert badly ("grinning like he knows" →
"like you knows"). Avoid pronoun+verb phrases in `description`/`base_description`;
prefer noun phrases ("the grin of someone with a secret").

### 20.6 Consumables use triggers, not legacy props

`effect_stat`/`effect_amount`/`effect_target` are deprecated legacy (task-329 removes
engine support). Author an `on_eat`/`on_drink` logic_trigger with `adjust_vital`
(+ `consume_item` for single-use food) and a `triggers` edge from the item. Verb coverage
is automatic: `eat` fires `on_eat`, and `use` falls back to `on_drink`/`on_eat` when no
`on_use` trigger exists (`item_actions.py:1508–1516`).

### 20.7 Library reuse pattern

Embed full node properties AND set `"library_id": "<library entry>"` so
`POST /api/library/refresh-to-world` can re-sync stale copies later. Display names may
differ from the library entry name.

### 20.8 Save Scenario rewrites your file

Saving exports the full denormalized format over the source scenario and adds character
placement `in` edges. Edits made to the source file after loading are lost on save —
patch the source before loading, or change things live via the inspector and let it save.

### 20.9 Emotion renders when set

`emotion: {"current": "...", "description": "...", "intensity": N}` produces affect lines
("miki doki is quite anxious."). Vitals thresholds add inner-life lines (Sanity tiers →
`=== YOUR MIND ===`, low Social → isolation line). Threshold wording context-awareness is
tracked as tasks 327/328.
