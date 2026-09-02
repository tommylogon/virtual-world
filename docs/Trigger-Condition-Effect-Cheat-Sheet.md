# Trigger, Condition & Effect Cheat Sheet

Complete reference for VirtualWorld engine behaviors and triggers.

**Legend:** 🔵 Triggers | 🟢 Behaviors | 🔴 Both

---

## Trigger Types (33)

| Trigger | Fires When | Used In |
|---------|------------|---------|
| `on_take` | Item picked up | 🔴 Both |
| `on_drop` | Item dropped | 🔴 Both |
| `on_examine` | Item examined | 🔴 Both |
| `on_inspect` | Right-click inspect in UI | 🔵 Triggers |
| `on_use` | Item used (generic) | 🔴 Both |
| `on_use_progressive` | Every progressive use (task-102) | 🔵 Triggers |
| `on_use_on` | Item used on a target (door, item, character) | 🔴 Both |
| `on_look` | Area looked at while item present | 🔵 Triggers |
| `on_search` | Player searches and finds hidden item | 🔵 Triggers |
| `on_tick` | Every tick while carried/equipped/lit | 🔴 Both |
| `on_eat` | Item eaten | 🔴 Both |
| `on_drink` | Item drunk | 🔴 Both |
| `on_read` | Item read | 🔴 Both |
| `on_light` | Item lit (torch, candle) | 🔴 Both |
| `on_activate` | Item activated | 🔴 Both |
| `on_equip` | Item equipped | 🔴 Both |
| `on_unequip` | Item unequipped | 🔴 Both |
| `on_throw` | Item thrown | 🔴 Both |
| `on_break` | Item breaks | 🔵 Triggers |
| `on_depleted` | Item uses reach 0 | 🔵 Triggers |
| `on_toggle_on` | Toggleable item turned on | 🔴 Both |
| `on_toggle_off` | Toggleable item turned off | 🔴 Both |
| `on_open` | Item/way opened | 🔴 Both |
| `on_close` | Item/way closed | 🔴 Both |
| `on_state_enter` | Node enters a specific `current_state` | 🔵 Triggers |
| `on_state_exit` | Node exits a specific `current_state` | 🔵 Triggers |
| `on_auto_open` | Way auto-opens during passage | 🔵 Triggers |
| `on_enter` | Player enters a room/area | 🔵 Triggers |
| `on_speech` | Speech matches near item | 🔵 Triggers |
| `on_fail_jump` | Jump attempt fails | 🔵 Triggers |
| `on_fail_climb` | Climb attempt fails | 🔵 Triggers |
| `on_delayed` | `schedule_trigger` delay elapses | 🔵 Triggers |
| `on_spoil` | Perishable item spoils | 🔵 Triggers |

---

## Condition Types (27 engine, 19 in UI)

| Condition | Checks | Params | UI | Used In |
|-----------|--------|--------|-----|---------|
| `eq` | Context key equals value | `target`, `value` | ❌ | 🟢 Behaviors |
| `in_area` | Target is in specific room | `target` (default "npc"), `area` | ❌ | 🟢 Behaviors |
| `tick_since_state` | N ticks since state entered | `min_ticks` | ❌ | 🟢 Behaviors |
| `proximity` | Target within N areas of NPC | `max_areas` | ❌ | 🟢 Behaviors |
| `has_item` | Player has item in inventory | `item` or `value` | ✅ | 🔴 Both |
| `has_items` | Player has ALL items | `value` (list) | ✅ | 🔴 Both |
| `random_chance` | True X% of the time | `value` (0-100) or `chance` (0.0-1.0) | ✅ | 🔴 Both |
| `uses_reached` | Item uses ≤ N | `value` (int) | ✅ | 🔵 Triggers |
| `uses_above` | Item uses > N | `value` (int) | ✅ | 🔵 Triggers |
| `state_equals` | Node's `current_state` matches | `target`, `value` | ✅ | 🔴 Both |
| `skill_check` | Skill check succeeds | `skill`, `dc` | ✅ | 🔴 Both |
| `save_throw` | Save throw succeeds | `stat`/`skill`, `dc`, `target` | ✅ | 🔴 Both |
| `temperature_below` | Room temp below threshold | `value` | ❌ | 🟢 Behaviors |
| `temperature_above` | Room temp above threshold | `value` | ❌ | 🟢 Behaviors |
| `area_temp` | Room temp with operator | `value`, `operator` (lt/le/eq/ge/gt) | ✅ | 🔴 Both |
| `vital` | Vital compares to value | `stat`, `value`, `operator`, `target` | ✅ | 🔴 Both |
| `vital_above` | Vital > threshold | `stat`, `value`, `target` | ✅ | 🔴 Both |
| `vital_below` | Vital < threshold | `stat`, `value`, `target` | ✅ | 🔴 Both |
| `is_equipped` | Player has item equipped | `item`, `target` | ✅ | 🔴 Both |
| `time_of_day` | Clock matches HH:MM | `value` (HH:MM) | ✅ | 🔴 Both |
| `weather` | Area weather matches | `value` | ✅ | 🔴 Both |
| `has_trait` | Player has trait | `value` (trait ID), `target` | ✅ | 🔴 Both |
| `has_tag` | Target has tag(s) | `value` (tag/list), `target` | ✅ | 🔴 Both |
| `target_has_tag` | Alias for has_tag target="target" | `value` (tag list) | ❌ | 🟢 Behaviors |
| `item_relationship` | Item has spatial/master edge | `relation`, `direction`, `target` | ✅ | 🔵 Triggers |
| `sound_heard` | Character heard sound pattern | `pattern` | ❌ | 🟢 Behaviors |
| `speech_matches` | Spoken text matches phrase | `phrase`/`value`, `mode` | ✅ | 🔵 Triggers |

**Compound operators:** `and`, `or`, `not` — 🔴 Both

---

## Effect Types (42 + 5 Python-only)

| Effect | Does | Params | UI | Used In |
|--------|------|--------|-----|---------|
| `message` | Output narrative text | `message` | ✅ | 🔴 Both |
| `destroy_self` | Remove triggering item | — | ✅ | 🔵 Triggers |
| `damage` | Deal damage | `amount`, `target`, `save` | ✅ | 🔴 Both |
| `save` | Save gate with branches | `stat`, `dc`, `on_success`, `on_fail` | ✅ | 🔴 Both |
| `heal` | Restore vital (capped 100) | `amount`, `stat`, `target` | ✅ | 🔴 Both |
| `spawn_item` | Create item node | `item_id`, `into`, `capture` | ✅ | 🔴 Both |
| `spawn_character` | Spawn from library | `character_id`, `area` | ✅ | 🔴 Both |
| `give_item` | Place item into inventory | `item_id`, `target` | ✅ | 🔴 Both |
| `remove_item` | Remove item node | `item_id` | ✅ | 🔴 Both |
| `consume_item` | Remove from inventory | `item_id`, `target` | ✅ | 🔴 Both |
| `set_state` | Change `current_state` | `node_id`, `state` | ✅ | 🔴 Both |
| `set_hidden` | Toggle hidden property | `node_id`, `hidden` | ✅ | 🔵 Triggers |
| `adjust_uses` | Change use count by delta | `node_id`, `delta` | ✅ | 🔵 Triggers |
| `end_scenario` | End the game | — | ✅ | 🔴 Both |
| `restart_scenario` | Restart the game | — | ✅ | 🔴 Both |
| `set_environment` | Override room env | `light`, `temperature`, etc. | ✅ | 🔴 Both |
| `adjust_environment` | Increment room env | `temperature`, `light`, etc. | ✅ | 🔴 Both |
| `teleport` | Move player to area | `area` | ✅ | 🔴 Both |
| `rename` | Rename a node | `node_id`, `name` | ✅ | 🔵 Triggers |
| `unlock_way` | Set door passable | `way_id` | ✅ | 🔵 Triggers |
| `set_description` | Replace description | `target`, `value` | ✅ | 🔵 Triggers |
| `append_description` | Append to description | `target`, `text` | ✅ | 🔵 Triggers |
| `adjust_vital` | Adjust vital (0-100) | `stat`, `amount`, `target` | ✅ | 🔴 Both |
| `add_tag` | Add tag to node | `node_id`, `tag` | ✅ | 🔵 Triggers |
| `remove_tag` | Remove tag from node | `node_id`, `tag` | ✅ | 🔵 Triggers |
| `apply_trait` | Add trait to character | `trait`, `target` | ✅ | 🔴 Both |
| `remove_trait` | Remove trait | `trait`, `target` | ✅ | 🔴 Both |
| `apply_condition` | Apply condition | `condition`, `target`, `duration`, `source` | ✅ | 🔴 Both |
| `remove_condition` | Remove condition | `condition`, `target` | ✅ | 🔴 Both |
| `set_parameter` | Set node parameter | `node_id`, `key`, `value` | ✅ | 🔵 Triggers |
| `adjust_parameter` | Delta to parameter | `node_id`, `key`, `delta` | ✅ | 🔵 Triggers |
| `surface_memory` | Force memory recall | `tags`, `salience_boost` | ✅ | 🟢 Behaviors |
| `suppress_memory` | Block memory recall | `keywords`, `duration` | ✅ | 🟢 Behaviors |
| `unblock_memory` | Lift memory block | `tags` | ✅ | 🟢 Behaviors |
| `schedule_trigger` | Queue delayed trigger | `delay_ticks`, `target` | ✅ | 🔵 Triggers |
| `spawn_way` | Create runtime way | `area_from`, `target`, `direction`, `state` | ✅ | 🔵 Triggers |
| `spawn_area` | Create new area | `name`, `environment` | ✅ | 🔵 Triggers |
| `set_way_target` | Rewire way connection | `way_id`, `target` | ✅ | 🔵 Triggers |
| `set_way_view` | Mutate way metadata | `way_id`, `see_through`, `state` | ✅ | 🔵 Triggers |
| `llm_respond` | Object speaks via LLM | `instructions`, `fallback_message` | ✅ | 🔵 Triggers |
| `scry` | Far-sight view | `target`, `message` | ✅ | 🔵 Triggers |
| `drain` | Reduce item uses (legacy) | `amount` | ✅ | 🔵 Triggers |
| `set_time` | Set game clock | `hour` or `HH:MM` | ❌ | 🔵 Triggers |
| `set_date` | Set calendar | `day`, `month`, `year` | ❌ | 🔵 Triggers |
| `set_weather` | Set global weather | `weather`, `duration_ticks` | ❌ | 🔵 Triggers |
| `forecast_override` | Lock forecast | `weather`, `wind`, `humidity`, `duration` | ❌ | 🔵 Triggers |
| `adjust_forecast` | Delta-shift forecast | `temperature_mod`, `light_mod` | ❌ | 🔵 Triggers |

---

## Common Examples

### Item: Torch that lights up
```json
{
  "trigger": "on_light",
  "effects": [
    { "type": "set_state", "node_id": "self", "state": "lit" },
    { "type": "message", "message": "The torch flares to life." }
  ]
}
```

### Door with fear save
```json
{
  "trigger": "on_open",
  "effects": [
    {
      "type": "save",
      "stat": "WIS",
      "dc": 12,
      "on_fail": [
        { "type": "apply_condition", "condition": "frightened", "target": "self" }
      ]
    }
  ]
}
```

### NPC hunts player in proximity
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "proximity", "max_areas": 2 },
    { "type": "state_equals", "target": "npc", "value": "hunting" }
  ],
  "effects": [
    { "type": "message", "message": "The shadow lunges toward you!" }
  ]
}
```

### Keycard door unlock
```json
{
  "trigger": "on_use_on",
  "conditions": [
    { "type": "has_item", "item": "red_keycard" }
  ],
  "effects": [
    { "type": "unlock_way", "way_id": "target" },
    { "type": "message", "message": "The scanner beeps green." }
  ]
}
```

### Progressive use item
```json
{
  "trigger": "on_use_progressive",
  "effects": [
    { "type": "adjust_uses", "node_id": "self", "delta": -1 },
    {
      "type": "message",
      "message": "You bandage the wound. Uses remaining: {uses_left}"
    }
  ]
}
```

### Scheduled delayed trap
```json
{
  "trigger": "on_open",
  "effects": [
    { "type": "message", "message": "You hear a click..." },
    { "type": "schedule_trigger", "delay_ticks": 3, "target": "self" }
  ]
}
```
```json
{
  "trigger": "on_delayed",
  "effects": [
    { "type": "damage", "amount": 10, "target": "self" },
    { "type": "message", "message": "Darts shoot from the walls!" }
  ]
}
```

---

## Discrepancies

- **5 weather/time effects** exist in Python handlers but are missing from `constants.py` and the JS editor — invisible to UI and flagged as unknown by validator
- **8 condition types** are engine-evaluated but not exposed in the JS editor dropdown (used by NPC behaviors/legacy)

---

## Behavior Actions (NPC Behavior System)

Simple NPC behavior actions are defined in `engine/triggers/behaviors.py` and edited via the behavior inspector UI.

| Action | Params | Notes |
|--------|--------|-------|
| `message` | `text` | NPC speech/action text |
| `speak` | `text` | Broadcast speech to area |
| `set_npc_state` | `state` | idle, curious, angry, hunting, etc. |
| `damage` | `amount`, `target` | player or self |
| `heal` | `amount`, `stat`, `target` | restore vital |
| `set_environment` | `stat`, `amount`, `area` | temperature, light |
| `spawn_item` | `item_id`, `name`, `description` | create item in area |
| `spawn_character` | `character_id`, `name`, `area` | spawn from library |
| `teleport` | `area`, `target` | move player/self |
| `go` | `mode`, `area`, `areas` | goto/random/patrol |
| `llm_respond` | `instructions`, `fallback_message`, `max_words` | queued LLM line |
| `add_memory` | `text`, `importance`, `tags` | store memory |
| `set_emotion` | `emotion`, `intensity` | emotion + 0-1 intensity |
| `set_flag` | `key`, `value` | arbitrary flag on NPC |
| `hide_in` | `target` | requires `hideable` tag |
| `hide_behind` | `target` | requires `hideable` tag |
| `hide_under` | `target` | requires `hideable` tag |
| `unhide` | — | remove hidden edges |
| `attack` | `target`, `weapon`, `where` | body part optional |
| `throw` | `item`, `target` | simplified throw |
| `break` | `item` | break target item |
| `take` | `item` | take from area |
| `drop` | `item` | drop in area |
| `put_in` | `item`, `container` | place item in container |
| `equip` | `item`, `slot` | optional slot |
| `unequip` | `item`, `slot` | optional slot/item |
| `use` | `item`, `target` | use or use_on |
| `eat` | `item` | consume food |
| `drink` | `item` | consume drink |
| `craft` | `recipe` | craft item |
| `combine` | `source`, `target` | combine items |
| `repair` | `item`, `kit` | repair item |
| `read` | `item` | read description |
| `open` | `target` | open item/way |
| `close` | `target` | close item |
| `lock` | `target` | lock item/way |
| `unlock` | `target` | unlock item/way |
| `push` | `target`, `direction` | push/pull object |
| `turn` | `target` | turn object |
| `search` | `target` | search container/area |
| `give` | `item`, `target` | give item to character |
| `steal` | `item`, `target` | steal from character |
| `follow` | `target` | follow character |
| `wait` | — | wait one turn |
| `dash` | `direction` | dash movement |
| `crawl` | `direction` | crawl movement |
| `climb` | `direction` | climb movement |
| `jump` | `direction` | jump movement |
| `toggle_way` | `direction`, `way_action` | open/close way |
| `grab` | `target` | grapple target |
| `drag` | `target`, `direction` | drag grappled target |
| `pin` | `target` | pin target |
| `struggle` | — | escape grapple |
| `escape` | — | escape grapple |
| `release` | `target` | release grapple |
| `look` | — | look around area |
| `examine` | `target` | examine item/character |
| `activate` | `item` | activate item |
| `light` | `item` | light item |
| `toggle` | `item` | toggle item status |
| `place` | `item`, `target`, `relation` | place item relation target |
| `stow` | `item` | stow item |
| `remove` | `item` | remove equipped item |
| `hold` | `item` | hold item |
| `weigh` | — | check encumbrance |
| `inventory` | — | list inventory |
| `carry` | `item` | pick up item |
| `dress` | — | get dressed |
| `strip` | — | undress |
| `swap` | `item`, `target` | swap equipment |
| `adorn` | `item`, `target` | adorn item on target |
| `rest` | `minutes` | rest |
| `sleep` | `minutes` | sleep |
| `meditate` | `minutes` | meditate |
| `bathe` | `target`, `minutes` | bathe |
| `sit` | — | sit down |
| `stand` | — | stand up |
| `stop` | — | stop activity |
| `wake` | `target` | wake self/target |
| `relieve` | — | relieve self |
| `fumble` | — | fumble around |
| `listen` | — | listen to area |
| `introduce` | `target` | introduce self |
| `beg` | `target` | beg target |
| `demand` | `target` | demand from target |
| `bribe` | `target`, `item` | bribe target with item |
| `trade` | `item`, `target` | trade item to target |
| `kiss` | `target`, `where`, `intensity` | intimacy action |
| `caress` | `target`, `where`, `intensity` | intimacy action |
| `lick` | `target`, `where`, `intensity` | intimacy action |
| `suck` | `target`, `where`, `intensity` | intimacy action |
| `bite` | `target`, `where`, `intensity` | intimacy action |
| `tickle` | `target`, `where`, `intensity` | intimacy action |
| `embrace` | `target`, `where`, `intensity` | intimacy action |
| `manifest` | — | ghost manifest |
| `vanish` | — | ghost vanish |
| `possess` | `target` | possess target |
| `wraith_form` | — | wraith form |
| `spawn_body_item` | — | spawn body item |
| `teach` | `target`, `subject` | teach recipe |
| `cook` | `recipe` | cook recipe |
| `push_through` | `direction` | push through gap |
| `block` | `target` | block target |
| `help` | — | show help |
| `commands` | — | show commands |
| `who` | — | show who is here |
| `time` | — | show game time |
| `score` | — | show status |
| `map` | — | show map |
| `save` | — | save game |
| `quit` | — | quit game |
| `version` | — | show version |

---

## Behavior Conditions (NPC Behavior System)

| Condition | Params | Notes |
|-----------|--------|-------|
| `eq` | `target`, `value` | exact match |
| `has_item` | `item`, `target` | player/npc |
| `has_trait` | `value` | trait ID |
| `has_tag` | `value` | tag string |
| `in_area` | `area`, `target` | area name |
| `random_chance` | `chance` | 0.0-1.0 |
| `tick_since_state` | `min_ticks` | ticks in state |
| `proximity` | `max_areas` | distance in areas |
| `npc_emotion_is` | `emotion`, `operator`, `value` | eq/gt/gte/lt/lte |
| `npc_is_hidden` | `value` | true/false |
| `character_has_tag` | `tag`, `target` | self/player/triggering |

**Compound operators:** `and`, `or`, `not`
