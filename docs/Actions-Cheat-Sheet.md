# Player & NPC Actions Cheat Sheet

Complete reference for every action verb in VirtualWorld.

**Status:** ✅ Implemented | ⚠️ Partial/alias | ❌ Missing/hallucinated
**Scope:** 🔵 Player | 🟢 NPC | 🔴 Both

---

## 1. Movement

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `go` | `move`, `walk` | ✅ | `movement.go` |
| `dash` | — | ✅ | `movement.dash_to_area` |
| `crawl` | — | ✅ | `movement.crawl_to_area` |
| `climb` | — | ✅ | `movement.climb_to_area` |
| `jump` | — | ✅ | `movement.jump_to_area` |
| `approach` | `approach to` | ✅ | `movement.approach` |
| `traverse` | — | ✅ | Delegates to `move_to_area` for NPC behaviors |
| `toggle way` | — | ❌ | Not a player verb; `toggle_way` is internal/open-close only |
| `wait` | `pass`, `rest` | ✅ | `tick_manager` |

---

## 2. Combat

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `attack` | `hit`, `strike`, `punch`, `kick`, `slash`, `shoot`, `stab` | ✅ | `combat.attack` |
| `throw` | — | ⚠️ | Simplified in behaviors; drops item instead of true projectile |
| `break` | — | ✅ | Sets item uses to 0 in NPC behaviors |
| `fumble around` | — | ✅ | `narration.fumble_around` |

---

## 3. Grappling

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `grab` | `grapple`, `seize`, `catch` | ✅ | `grapple.grab` |
| `drag` | `pull` | ✅ | `grapple.drag` |
| `pin` | `pin down` | ✅ | Uses `grapple.grab` + adds `pinned` condition |
| `struggle` | `resist` | ✅ | `grapple.escape` |
| `escape` | `break free`, `get free` | ✅ | `grapple.escape` |
| `release` | `let go`, `unhold` | ✅ | `grapple.release` |

---

## 4. Items — General

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `use` | — | ✅ | `use_actions.use_item` |
| `activate` | — | ❌ | No `use_actions.activate` |
| `light` | `ignite`, `burn` | ⚠️ | Alias for `use`/`toggle_item_status`; no dedicated light verb |
| `toggle` | — | ✅ | `toggleable_items.toggle_item_status` |
| `place` | `put`, `set`, `lay` | ✅ | `place_actions.place_item` |
| `combine` | `mix`, `blend`, `forge` | ✅ | `crafting.combine_items` |
| `carve` | `engrave`, `decorate` | ❌ | No `crafting.decorate` verb |
| `stow` | `store`, `put away` | ✅ | `stacking.stow_item` |
| `steal` | `pickpocket` | ✅ | `transfer_actions.steal_item` |
| `repair` | `fix`, `mend`, `patch` | ❌ | No `crafting.repair_item` |
| `read` | — | ✅ | Via `examine` text reveal |

---

## 5. Inventory Management

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `take` | `get`, `pickup`, `grab`, `pick up` | ✅ | `take_drop_actions.take_item` |
| `drop` | — | ✅ | `take_drop_actions.drop_item` |
| `put (in)` | `place (in)`, `insert` | ✅ | `take_drop_actions.put_in_container` |
| `remove` | `take off` | ✅ | `take_drop_actions.remove_held` |
| `hold` | `grip` | ❌ | Not a command verb |
| `weigh` | `measure` | ❌ | Not a command verb |
| `inventory` | `inv`, `i`, `look down` | ✅ | `item_actions.get_inventory` |
| `carry` | `lift` | ⚠️ | Alias for `take` |

---

## 6. Equipment

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `equip` | `wear`, `don`, `put on` | ✅ | `equipment.equip_item` |
| `unequip` | `remove`, `take off` | ✅ | `equipment.unequip_item` |
| `dress` | `get dressed`, `clothe` | ✅ | `activities.dress` |
| `strip` | `undress`, `disrobe` | ✅ | `activities.strip` |
| `swap` | `exchange` | ❌ | No `equipment.swap_equipment` |
| `adorn` | `bedeck` | ❌ | No `crafting.decorate` verb |

---

## 7. Consumption

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `eat` | `bite`, `nibble`, `devour`, `consume` | ✅ | `consume_actions.eat_item` |
| `drink` | `swig`, `sip`, `gulp`, `quaff` | ✅ | `consume_actions.drink_item` |
| `gulp down` | — | ✅ | Uses `_consume_item` pipeline in NPC behaviors |

---

## 8. Crafting / Combination

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `craft` | `make`, `build`, `create` | ✅ | `crafting.craft_item` |
| `combine` | — | ✅ | `crafting.combine_items` |
| `teach` | — | ✅ | `crafting.teach_item` |
| `cook` | `brew`, `distill` | ❌ | No `crafting.cook_item` |
| `repair` | — | ❌ | No `crafting.repair_item` |

---

## 9. Ghost

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `manifest` | `phase in` | ❌ | No `ghost.manifest` verb |
| `vanish` | `phase out`, `disappear` | ❌ | No `ghost.vanish` verb |
| `possess` | `enter` | ❌ | No `ghost.possess` verb |
| `wraith form` | — | ❌ | No `ghost.ghost_tint` verb |
| `spawn body item` | — | ❌ | No `ghost.spawn_body_item` verb |

---

## 10. Social / Speech

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `say` | `speak`, `tell`, `ask`, `exclaim` | ✅ | `broadcast_speech` (normal) |
| `whisper` | `mutter`, `hiss` | ✅ | `broadcast_speech` (whisper) |
| `shout` | `yell`, `holler`, `bellow` | ✅ | `broadcast_speech` (shout) |
| `scream` | `shriek` | ✅ | `broadcast_speech` (scream) |
| `sing` | `hum`, `laugh`, `cry`, `recite` | ✅ | `broadcast_speech` (sing) |
| `introduce` | `greet` | ❌ | No `social.introduce` |
| `beg` | `plead`, `propose` | ❌ | No `social.*` verb |
| `demand` | `order`, `threaten` | ❌ | No `social.*` verb |
| `bribe` | — | ❌ | No `social.*` verb |
| `follow` | `lead`, `accompany` | ❌ | No `social.follow` verb |
| `trade` | `barter`, `swap` | ⚠️ | Alias for `give` |

---

## 11. Emotes

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `do` | `emote`, `act`, `gesture` | ✅ | `narration.process_emote` |

---

## 12. Intimacy (Mature-Gated)

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `kiss` | — | ✅ | `pleasure.kiss` |
| `caress` | `pet`, `stroke` | ✅ | `pleasure.caress` |
| `lick` | — | ✅ | `pleasure.lick` |
| `suck` | `blow` | ✅ | `pleasure.suck` |
| `bite` | — | ✅ | `pleasure.bite` |
| `pinch` | — | ✅ | `pleasure.pinch` |
| `tickle` | — | ❌ | No `pleasure.ticklish` |
| `embrace` | `hug`, `cuddle`, `snuggle` | ✅ | `pleasure.embrace` |

---

## 13. Activities / Status

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `rest` | `sleep`, `lie down`, `lay down` | ✅ | `activities.start` |
| `meditate` | `focus`, `contemplate` | ✅ | `activities.meditate` |
| `bathe` | `bath`, `wash` | ✅ | `activities.bathe` |
| `sit` | `sit down`, `perch` | ✅ | `activities.sit` |
| `stand` | `stand up`, `get up`, `rise` | ✅ | `activities.stand` |
| `wait` | `linger` | ✅ | `activities.wait` |
| `stop` | `quit`, `halt`, `abort` | ✅ | `activities.stop` |
| `wake` | `awaken` | ✅ | `activities.wake` |
| `dress` | `get dressed` | ✅ | `activities.dress` |
| `strip` | `undress` | ✅ | `activities.strip` |
| `relieve` | `relieve oneself` | ✅ | `activities.relieve_self` |
| `read` | — | ✅ | Via `examine` text reveal |
| `listen` | — | ✅ | `narration.listen` |
| `fumble around` | `grope`, `feel around` | ✅ | `narration.fumble_around` |
| `lie down` | `lay down` | ✅ | `activities.lie_down` |
| `fix` | `treat` | ✅ | `activities.fix` |

---

## 14. Environmental Interaction

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `open` | — | ✅ | `item_actions.open` / `movement.open` |
| `close` | — | ✅ | `item_actions.close_item` |
| `lock` | — | ✅ | `item_actions.lock_item` |
| `unlock` | — | ✅ | `item_actions.lock_item` |
| `push` | `pull`, `move (object)` | ✅ | `item_actions.push_pull` |
| `turn` | `rotate`, `spin` | ✅ | `item_actions.turn` |
| `drag` | — | ✅ | `item_actions.push_pull` |
| `push through` | `squeeze` | ✅ | Delegates to `move_to_area` in NPC behaviors |
| `climb` | `swing`, `vault`, `leap` | ✅ | `movement.climb_to_area` |
| `block` | `barricade` | ❌ | No `crafting.place_obstacle` verb |

---

## 15. Search / Examine

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `look` | `l`, `scan` | ✅ | `examine_actions` |
| `examine` | `inspect`, `check`, `look at`, `describe` | ✅ | `examine_actions` |
| `search` | `rummage`, `root through`, `probe` | ✅ | `item_actions.search` |
| `listen` | — | ✅ | `narration.listen` |
| `read` | — | ✅ | Via `examine` |
| `inventory` | `inv`, `i` | ✅ | `get_inventory` |
| `find` | — | ✅ | Alias/helper for search |
| `split` | — | ✅ | `crafting.split_item` |

---

## 16. System / Info

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `help` | — | ❌ | No `action_handlers.help` verb |
| `commands` | `verbs` | ❌ | No `action_handlers.commands` verb |
| `who` | `whoami` | ❌ | No `whoami` verb |
| `time` | `date` | ❌ | No `world.time` verb |
| `stats` | `status` | ✅ | `get_status` / `format_vitals_readout` |
| `map` | `north` | ❌ | No `report_map` verb |
| `save` | — | ❌ | Session control only; not a game verb |
| `quit` | `exit` | ❌ | Session control only; not a game verb |
| `version` | `about` | ❌ | No `version` verb |

---

## 17. Special / Meta

| Verb | Aliases | Status | Notes |
|------|---------|--------|-------|
| `drop all` | `empty`, `dump` | ✅ | Uses `drop_held_items` + carried items in NPC behaviors |
| `give` | — | ✅ | `transfer_actions.give_item` |
| `take all` | `loot` | ✅ | Takes all reachable items in NPC behaviors |
| `steal` | `pickpocket` | ✅ | `transfer_actions.steal_item` |
| `follow` | — | ❌ | No `social.follow` verb |
| `lead` | — | ✅ | `grapple.lead` |
| `bind` | `enchant` | ✅ | Agent/item trigger authoring |
| `emote` | `do`, `act`, `gesture` | ✅ | `narration.process_emote` |

---

## Missing from Cheat Sheet but Implemented

| Verb | Handler | Notes |
|------|---------|-------|
| `find` | search alias | Search helper |
| `split` | `crafting.split_item` | Split stackable items |
| `fix` / `treat` | `activities.fix` | Treat wounds |
| `lead` | `grapple.lead` | Lead character by hand |
| `bind` / `enchant` | trigger authoring | Create item triggers at runtime |

---

## Summary

- **Total verbs documented:** 83
- **Actually implemented:** ~52
- **Partial/alias:** ~8
- **Missing/hallucinated:** ~23

Biggest hallucination clusters: ghost powers, social verbs (`introduce`, `beg`, `demand`, `bribe`, `follow`), system/info commands (`help`, `commands`, `who`, `time`, `map`, `save`, `quit`, `version`), and some item/environment verbs (`activate`, `carve`, `repair`, `block`).

Implemented in NPC behavior system this session: `traverse`, `push_through`, `break`, `pin`, `gulp_down`, `drop_all`, `take_all`.
