# Player & NPC Actions Cheat Sheet

Complete reference for every action verb in VirtualWorld.

**Scope:** 🔵 Player | 🟢 NPC | 🔴 Both

---

## 1. Movement

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `go` | `move`, `walk` | `movement.go` | 🔴 | `go north` |
| `dash` | — | `movement.dash_to_area` | 🔵 | `dash east` |
| `crawl` | — | `movement.crawl_to_area` | 🔵 | `crawl north` |
| `climb` | — | `movement.climb_to_area` | 🔴 | `climb tree` / `climb up` |
| `jump` | — | `movement.jump_to_area` | 🔴 | `jump` / `jump over ledge` |
| `approach` | `approach to` | `movement.approach` | 🔴 | `approach the guard` |
| `traverse` | — | `movement.traverse` | 🔴 | `traverse chasm` |
| `toggle way` | — | `movement.toggle_way` | 🔵 | `toggle way` |
| `wait` | `pass`, `rest` | `tick_manager` | 🔴 | `wait` |

---

## 2. Combat

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `attack` | `hit`, `strike`, `punch`, `kick`, `slash`, `shoot`, `stab` | `combat.attack` | 🔴 | `attack goblin with sword` |
| `throw` | — | `combat.throw` | 🔴 | `throw knife at orc` |
| `break` | — | `item_actions.break_item` | 🔴 | `break bottle` |
| `fumble around` | — | `narration.fumble_around` | 🔵 | `fumble around` |

---

## 3. Grappling

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `grab` | `grapple`, `seize`, `catch` | `grapple.grab` | 🔴 | `grab prisoner` |
| `drag` | `pull` | `grapple.drag` | 🔴 | `drag body north` |
| `pin` | `pin down` | `grapple.pin` | 🔴 | `pin bandit` |
| `struggle` | `resist` | `grapple.escape` | 🔴 | `struggle` |
| `escape` | `break free`, `get free` | `grapple.escape` | 🔴 | `escape` |
| `release` | `let go`, `unhold` | `grapple.release` | 🔴 | `release captive` |

---

## 4. Items — General

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `use` | — | `use_actions.use_item` | 🔴 | `use lantern` / `use key on door` |
| `activate` | — | `use_actions.activate` | 🔴 | `activate panel` |
| `light` | `ignite`, `burn` | `toggleable_items.light` | 🔴 | `light torch` |
| `toggle` | — | `toggleable_items.toggle` | 🔴 | `toggle switch` |
| `place` | `put`, `set`, `lay` | `place_actions.place_item` | 🔴 | `put apple on table` |
| `combine` | `mix`, `blend`, `forge` | `crafting.combine_items` | 🔴 | `combine cloth with stick` |
| `carve` | `engrave`, `decorate` | `crafting.decorate` | 🔴 | `carve symbol into wood` |
| `stow` | `store`, `put away` | `stacking.stow_item` | 🔴 | `stow sword in chest` |
| `steal` | `pickpocket` | `transfer_actions.steal_item` | 🔴 | `steal coin purse from merchant` |
| `repair` | `fix`, `mend`, `patch` | `crafting.repair_item` | 🔴 | `repair armor with kit` |
| `read` | — | `examine` (text reveal) | 🔴 | `read letter` |

---

## 5. Inventory Management

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `take` | `get`, `pickup`, `grab`, `pick up` | `take_drop_actions.take_item` | 🔴 | `take apple` |
| `drop` | — | `take_drop_actions.drop_item` | 🔴 | `drop sword` |
| `put (in)` | `place (in)`, `insert` | `take_drop_actions.put_in_container` | 🔴 | `put gem in box` |
| `remove` | `take off` | `take_drop_actions.remove_held` | 🔴 | `remove ring` |
| `hold` | `grip` | equip-style (off-slot) | 🔵 | `hold lantern` |
| `weigh` | `measure` | `carry_weight.report_encumbrance` | 🔵 | `weigh pack` |
| `inventory` | `inv`, `i`, `look down` | `item_actions.get_inventory` | 🔴 | `i` |
| `carry` | `lift` | `take_drop_actions.take_item` | 🔴 | `lift crate` |

---

## 6. Equipment

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `equip` | `wear`, `don`, `put on` | `equipment.equip_item` | 🔴 | `equip helmet` / `wear ring on finger` |
| `unequip` | `remove`, `take off` | `equipment.unequip_item` | 🔴 | `unequip armor` |
| `dress` | `get dressed`, `clothe` | `activities.dress` | 🔵 | `dress` |
| `strip` | `undress`, `disrobe` | `activities.strip` | 🔵 | `strip` |
| `swap` | `exchange` | `equipment.swap_equipment` | 🔴 | `swap helmets with guard` |
| `adorn` | `bedeck` | `crafting.decorate` | 🔴 | `adorn cloak with pin` |

---

## 7. Consumption

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `eat` | `bite`, `nibble`, `devour`, `consume` | `consume_actions.eat_item` | 🔴 | `eat bread` |
| `drink` | `swig`, `sip`, `gulp`, `quaff` | `consume_actions.drink_item` | 🔴 | `drink potion` |
| `gulp down` | — | `consume_actions.consume_bulk` | 🔴 | `gulp down potion` |

---

## 8. Crafting / Combination

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `craft` | `make`, `build`, `create` | `crafting.craft_item` | 🔴 | `craft campfire` |
| `combine` | — | `crafting.combine_items` | 🔴 | `combine cloth with stick` |
| `teach` | — | `crafting.teach_item` | 🔴 | `teach recipe to apprentice` |
| `cook` | `brew`, `distill` | `crafting.cook_item` | 🔴 | `cook stew in pot` |
| `repair` | — | `crafting.repair_item` | 🔴 | `repair armor with kit` |

---

## 9. Ghost

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `manifest` | `phase in` | `ghost.manifest` | 🔵 | `manifest` |
| `vanish` | `phase out`, `disappear` | `ghost.vanish` | 🔵 | `vanish` |
| `possess` | `enter` | `ghost.possess` | 🔵 | `possess mirror` |
| `wraith form` | — | `ghost.ghost_tint` | 🔵 | (state toggle) |
| `spawn body item` | — | `ghost.spawn_body_item` | 🔵 | (on death) |

---

## 10. Social / Speech

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `say` | `speak`, `tell`, `ask`, `exclaim` | `broadcast_speech` (normal) | 🔴 | `say Hello there!` |
| `whisper` | `mutter`, `hiss` | `broadcast_speech` (whisper) | 🔴 | `whisper Come here` |
| `shout` | `yell`, `holler`, `bellow` | `broadcast_speech` (shout) | 🔴 | `shout Fire!` |
| `scream` | `shriek` | `broadcast_speech` (scream) | 🔴 | `scream` |
| `sing` | `hum`, `laugh`, `cry`, `recite` | `broadcast_speech` (sing) | 🔴 | `sing a ballad` |
| `introduce` | `greet` | `social.introduce` | 🔴 | `greet the stranger` |
| `beg` | `plead`, `propose` | `social.*` | 🔴 | `beg for mercy` |
| `demand` | `order`, `threaten` | `social.*` | 🔴 | `demand answers` |
| `bribe` | — | `social.*` | 🔴 | `bribe guard` |
| `follow` | `lead`, `accompany` | `social.follow` | 🔴 | `follow guard` |
| `trade` | `barter`, `swap` | `transfer_actions.give_item` | 🔴 | `trade sword for potion` |

---

## 11. Emotes

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `do` | `emote`, `act`, `gesture` | `narration.process_emote` | 🔴 | `do raises an eyebrow` |

---

## 12. Intimacy (Mature-Gated)

> **Gated:** These verbs are filtered from client-side VERBS unless `state.matureContent` is true. NPCs can still receive them from engine scripts.

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `kiss` | — | `pleasure.kiss` | 🔴 | `kiss me` |
| `caress` | `pet`, `stroke` | `pleasure.caress` | 🔴 | `caress neck` |
| `lick` | — | `pleasure.lick` | 🔴 | `lick wound` |
| `suck` | `blow` | `pleasure.suck` | 🔴 | `blow gently` |
| `bite` | — | `pleasure.bite` | 🔴 | `bite lip` |
| `pinch` | — | `pleasure.pinch` | 🔴 | `pinch cheek` |
| `tickle` | — | `pleasure.ticklish` | 🔴 | `tickle ribs` |
| `embrace` | `hug`, `cuddle`, `snuggle` | `pleasure.embrace` | 🔴 | `hug tightly` |

**Intensity modifiers:** `soft`, `gentle`, `rough`, `hard`, `slowly`

**Body-part targeting:** `{"action":"caress","target":"lydia","where":"neck","intensity":"light|normal|firm"}`

---

## 13. Activities / Status

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `rest` | `sleep`, `lie down`, `lay down` | `activities.start` | 🔵 | `sleep` |
| `meditate` | `focus`, `contemplate` | `activities.meditate` | 🔵 | `meditate` |
| `bathe` | `bath`, `wash` | `activities.bathe` | 🔵 | `bathe` |
| `sit` | `sit down`, `perch` | `activities.sit` | 🔵 | `sit chair` |
| `stand` | `stand up`, `get up`, `rise` | `activities.stand` | 🔵 | `stand` |
| `wait` | `linger` | `activities.wait` | 🔵 | `wait` |
| `stop` | `quit`, `halt`, `abort` | `activities.stop` | 🔵 | `stop sleeping` |
| `wake` | `awaken` | `activities.wake` | 🔵 | `wake` |
| `dress` | `get dressed` | `activities.dress` | 🔵 | `get dressed` |
| `strip` | `undress` | `activities.strip` | 🔵 | `strip` |
| `relieve` | `relieve oneself` | `activities.relieve_self` | 🔵 | `relieve` |
| `read` | — | `activities.read_book` | 🔵 | `read book` |
| `listen` | — | `narration.listen` | 🔵 | `listen` |

---

## 14. Environmental Interaction

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `open` | — | `item_actions.open` / `movement.open` | 🔴 | `open door` |
| `close` | — | `item_actions.close_item` | 🔴 | `close chest` |
| `lock` | — | `item_actions.lock_item` | 🔴 | `lock door` |
| `unlock` | — | `item_actions.lock_item` | 🔴 | `unlock door with key` |
| `push` | `pull`, `move (object)` | `item_actions.push_pull` | 🔴 | `push boulder north` |
| `turn` | `rotate`, `spin` | `item_actions.turn` | 🔴 | `turn wheel` |
| `drag` | — | `item_actions.push_pull` | 🔴 | `drag crate` |
| `push through` | `squeeze` | `movement.push_through` | 🔴 | `squeeze through gap` |
| `climb` | `swing`, `vault`, `leap` | `movement` | 🔴 | `swing from rope` |
| `block` | `barricade` | `crafting.place_obstacle` | 🔴 | `barricade door` |

---

## 15. Search / Examine

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `look` | `l`, `scan` | `examine_actions` | 🔴 | `look` / `look north` |
| `examine` | `inspect`, `check`, `look at`, `describe` | `examine_actions` | 🔴 | `examine sword` |
| `search` | `rummage`, `root through`, `probe` | `item_actions.search` | 🔴 | `search desk` |
| `listen` | — | `narration.listen` | 🔴 | `listen` |
| `read` | — | `examine` (text reveal) | 🔴 | `read sign` |
| `inventory` | `inv`, `i` | `get_inventory` | 🔴 | `i` |

---

## 16. System / Info

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `help` | — | `action_handlers.help` | 🔵 | `help` |
| `commands` | `verbs` | `action_handlers.help` | 🔵 | `commands` |
| `who` | `whoami` | `whoami` | 🔵 | `who` |
| `time` | `date` | `world.time` | 🔴 | `time` |
| `score` | `stats`, `status` | `get_status` | 🔵 | `status` |
| `map` | `north` (compass) | `report_map` | 🔵 | `map` |
| `save` | — | session control | 🔵 | `save` |
| `quit` | `exit` | session control | 🔵 | `quit` |
| `version` | `about` | info | 🔵 | `version` |

---

## 17. Special / Meta

| Verb(s) | Aliases | Handler | Scope | Example |
|---------|---------|---------|-------|---------|
| `drop all` | `empty`, `dump` | `drop_item_all` | 🔴 | `drop all` |
| `give` | — | `transfer_actions.give_item` | 🔴 | `give apple to bob` |
| `take all` | `loot` | `take_item_all` | 🔴 | `take all` |
| `steal` | `pickpocket` | `transfer_actions.steal_item` | 🔴 | `steal coin from merchant` |
| `follow` | — | `social.follow` | 🔴 | `follow guard` |

---

## Alias Normalization

The engine normalizes these aliases to their canonical verb:

| Alias | Canonical |
|-------|-----------|
| `inspect`, `check`, `look at`, `describe` | `examine` |
| `read` | `examine` (text reveal) |
| `get`, `pickup`, `grab`, `pick up` | `take` |
| `put on`, `don`, `wear` | `equip` |
| `take off`, `remove`, `undress` | `unequip` |
| `say`, `speak`, `tell`, `ask`, `exclaim` | `say` |
| `whisper`, `mutter` | `whisper` |
| `shout`, `yell`, `holler`, `bellow` | `shout` |
| `scream`, `shriek` | `scream` |
| `sing`, `hum`, `laugh`, `recite` | `sing` |
| `do`, `emote`, `act`, `gesture` | `emote` |

---

## Structured Action JSON Examples

The LLM emits these as JSON objects:

```json
{"action": "go", "target": "north"}
{"action": "take", "item": "apple"}
{"action": "use", "item": "key", "target": "door"}
{"action": "attack", "target": "goblin", "weapon": "sword"}
{"action": "give", "item": "apple", "target": "bob"}
{"action": "say", "speech": "Hello!", "volume": "whisper"}
{"action": "emote", "text": "raises an eyebrow"}
{"action": "kiss", "target": "lydia", "where": "lips", "intensity": "normal"}
{"action": "caress", "target": "lydia", "where": "neck", "intensity": "light"}
{"action": "examine", "item": "sword"}
{"action": "search", "target": "desk"}
{"action": "equip", "item": "helmet"}
{"action": "craft", "item": "campfire"}
{"action": "combine", "item": "cloth", "target": "stick"}
{"action": "teleport", "target": "cellar"}
```

---

## Mature Content Gating

Intimacy verbs (`kiss`, `caress`, `lick`, `suck`, `bite`, `pinch`, `tickle`, `embrace`, etc.) are:
- **Present** in engine (`engine/pleasure_actions.py`)
- **Filtered** from client-side VERBS unless `state.matureContent` is true
- **Still usable** by NPCs via engine scripts regardless of gate
