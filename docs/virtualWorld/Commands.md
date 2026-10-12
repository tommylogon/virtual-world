---
type: doc
tags: [system/gameplay, surface/in-game]
---

# Commands

Every action verb in VirtualWorld, with its aliases, and the **feature page**
that documents it. This is a lookup table, not the documentation: the verbs are
a feature's *mechanics*, so the rules live on the feature page and this index
points at it.

**Status:** ✅ implemented · ⚠️ partial or alias · ❌ missing (listed so nobody
builds a second one)

**How to read the last column:** it names the feature page and the section that
owns the verb. Where it says `—`, no page owns it yet — that is a real gap, not
an omission.

---

## Movement

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `go` | `move`, `walk` | ✅ | [[World Building/Movement\|Movement]] — *The verbs* |
| `dash` | — | ✅ | [[World Building/Movement\|Movement]] — *Dash* |
| `crawl` | — | ✅ | [[World Building/Movement\|Movement]] — *The verbs* |
| `climb` | `swing`, `vault`, `leap` | ✅ | [[World Building/Movement\|Movement]] — *The verbs* |
| `jump` | — | ✅ | [[World Building/Movement\|Movement]] — *The verbs* |
| `approach` | `approach to` | ✅ | [[World Building/Movement\|Movement]] — *The verbs* |
| `traverse` | — | ✅ | [[World Building/Movement\|Movement]] — *The verbs* |
| `push through` | `squeeze` | ✅ | [[World Building/Movement\|Movement]] — *Crossing a way* |
| `wait` | `pass`, `linger` | ✅ | [[Gameplay/Turn Queue & Human Turns\|Turns]] |
| `toggle way` | — | ❌ | internal only; not a player verb |

## Combat and grappling

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `attack` | `hit`, `strike`, `punch`, `kick`, `slash`, `shoot`, `stab` | ✅ | [[Rules Engine/Combat System\|Combat]] |
| `grab` | `grapple`, `seize`, `catch` | ✅ | [[Rules Engine/Combat System\|Combat]] |
| `drag` | `pull` | ✅ | [[Rules Engine/Combat System\|Combat]] — *Moving as a group* |
| `pin` | `pin down` | ✅ | [[Rules Engine/Combat System\|Combat]] |
| `struggle` | `resist` | ✅ | [[Rules Engine/Combat System\|Combat]] |
| `escape` | `break free`, `get free` | ✅ | [[Rules Engine/Combat System\|Combat]] |
| `release` | `let go`, `unhold` | ✅ | [[Rules Engine/Combat System\|Combat]] |
| `lead` | — | ✅ | [[Rules Engine/Combat System\|Combat]] — *Moving as a group* |
| `throw` | — | ⚠️ | drops the item; no true projectile |
| `break` | — | ✅ | sets an item's `uses` to 0 |

## Items and inventory

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `take` | `get`, `pickup`, `pick up`, `carry`, `lift` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `drop` | — | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `drop all` | `empty`, `dump` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `take all` | `loot` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `put (in)` | `place (in)`, `insert` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `give` | — | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `steal` | `pickpocket` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `trade` | `barter`, `swap` | ⚠️ | alias for `give` |
| `use` | — | ✅ | [[Items & Inventory/Items Overview\|Items]] — *Use / use on* |
| `light` | `ignite`, `burn` | ⚠️ | alias for `use` / `toggle item status` |
| `toggle` | — | ✅ | [[Items & Inventory/Item States & Toggleables\|Item States]] |
| `place` | `put`, `set`, `lay` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `stow` | `store`, `put away` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `inventory` | `inv`, `i`, `look down` | ✅ | [[Items & Inventory/Inventory\|Inventory]] |
| `remove` | `take off` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `read` | — | ✅ | [[Items & Inventory/Items Overview\|Items]] — *Read / write* |
| `activate` | — | ❌ | no such verb; use `use` |
| `hold` / `weigh` | — | ❌ | not command verbs |

## Equipment

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `equip` | `wear`, `don`, `put on` | ✅ | [[Items & Inventory/Equipment & Paperdoll\|Equipment]] |
| `unequip` | `remove`, `take off` | ✅ | [[Items & Inventory/Equipment & Paperdoll\|Equipment]] |
| `dress` | `get dressed`, `clothe` | ✅ | [[Characters/Activities & States\|Activities]] |
| `strip` | `undress`, `disrobe` | ✅ | [[Characters/Activities & States\|Activities]] |
| `swap` / `adorn` | — | ❌ | no such verbs |

## Consumption

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `eat` | `bite`, `nibble`, `devour`, `consume` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `drink` | `swig`, `sip`, `gulp`, `quaff` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `gulp down` | — | ✅ | [[Items & Inventory/Items Overview\|Items]] |

## Crafting

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `craft` | `make`, `build`, `create` | ✅ | — *(no page yet; see [[Feature Map]])* |
| `combine` | `mix`, `blend`, `forge` | ✅ | — *(no page yet)* |
| `split` | — | ✅ | — *(no page yet)* |
| `teach` | — | ✅ | — *(no page yet)* |
| `cook` / `repair` / `carve` | `brew`, `distill`, `fix`, `mend`, `engrave` | ❌ | no such verbs |

## Speech and social

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `say` | `speak`, `tell`, `ask`, `exclaim` | ✅ | [[Characters/NPC Behavior System\|Speech]] |
| `whisper` | `mutter`, `hiss` | ✅ | [[Characters/NPC Behavior System\|Speech]] |
| `shout` | `yell`, `holler`, `bellow` | ✅ | [[Characters/NPC Behavior System\|Speech]] |
| `scream` | `shriek` | ✅ | [[Characters/NPC Behavior System\|Speech]] |
| `sing` | `hum`, `laugh`, `cry`, `recite` | ✅ | [[Characters/NPC Behavior System\|Speech]] |
| `name` | — | ✅ | [[Characters/NPC Behavior System\|Speech]] |
| `label` | — | ✅ | [[Characters/Relationships System\|Relationships]] |
| `introduce` / `beg` / `demand` / `bribe` / `follow` | — | ❌ | no such verbs |

## Emotes

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `do` | `emote`, `act`, `gesture` | ✅ | [[AI & Narration/Narration System\|Narration]] |

## Activities and status

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `rest` | `sleep`, `lie down`, `lay down` | ✅ | [[Characters/Activities & States\|Activities]] |
| `meditate` | `focus`, `contemplate` | ✅ | [[Characters/Activities & States\|Activities]] |
| `bathe` | `bath`, `wash` | ✅ | [[Characters/Activities & States\|Activities]] |
| `sit` | `sit down`, `perch` | ✅ | [[Characters/Activities & States\|Activities]] |
| `stand` | `stand up`, `get up`, `rise` | ✅ | [[Characters/Activities & States\|Activities]] |
| `stop` | `quit`, `halt`, `abort` | ✅ | [[Characters/Activities & States\|Activities]] |
| `wake` | `awaken` | ✅ | [[Characters/Activities & States\|Activities]] |
| `relieve` | `relieve oneself` | ✅ | [[Characters/Activities & States\|Activities]] |
| `fix` | `treat` | ✅ | [[Characters/Activities & States\|Activities]] |
| `lie down` | `lay down` | ✅ | [[Characters/Activities & States\|Activities]] |

## Looking and knowing

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `look` | `l`, `scan` | ✅ | [[Rooms & Areas]] |
| `examine` | `inspect`, `check`, `look at`, `describe` | ✅ | [[Rooms & Areas]] |
| `search` | `rummage`, `root through`, `probe` | ✅ | [[Gameplay/Search & Forage\|Search & forage]] |
| `find` | — | ✅ | alias/helper for `search` |
| `listen` | — | ✅ | [[AI & Narration/Narration System\|Narration]] |
| `fumble around` | `grope`, `feel around` | ✅ | [[World Building/Movement\|Movement]] — *Blindness* |
| `guess time` | — | ✅ | [[Environment/Time & Weather\|Time & weather]] |
| `stats` | `status` | ✅ | [[Characters/Vitals System\|Vitals]] |

## Ways and the environment

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `open` | — | ✅ | [[World Building/Movement\|Movement]] — *Crossing a way* |
| `close` | — | ✅ | [[World Building/Ways\|Ways]] |
| `lock` | — | ✅ | [[World Building/Ways\|Ways]] |
| `unlock` | — | ✅ | [[World Building/Ways\|Ways]] |
| `push` | `pull`, `move (object)` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `turn` | `rotate`, `spin` | ✅ | [[Items & Inventory/Items Overview\|Items]] |
| `block` | `barricade` | ❌ | no such verb |

## Intimacy (mature-gated)

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `kiss` | — | ✅ | — *(no page yet)* |
| `caress` | `pet`, `stroke` | ✅ | — *(no page yet)* |
| `embrace` | `hug`, `cuddle`, `snuggle` | ✅ | — *(no page yet)* |
| `lick` / `suck` / `bite` / `pinch` | `blow` | ✅ | — *(no page yet)* |
| `tickle` | — | ❌ | no such verb |

## Ghost and meta

| Verb | Aliases | Status | Documented in |
|---|---|---|---|
| `manifest` / `vanish` / `possess` / `wraith form` | — | ❌ | no such verbs; ghosts move freely (see [[World Building/Movement\|Movement]]) |
| `bind` | `enchant` | ✅ | [[Rules Engine/Triggers & Effects\|Triggers & effects]] |
| `help` / `commands` / `who` / `time` / `map` / `save` / `quit` / `version` | — | ❌ | not game verbs; session control or absent |

---

## Summary

- **Verbs listed:** 117 · **implemented:** 88 · **partial/alias:** 8 · **missing:** 21
- The biggest missing clusters are ghost powers, social verbs, and system/info
  commands.
- Verbs implemented only in the NPC behaviour path: `traverse`, `push through`,
  `break`, `pin`, `gulp down`, `drop all`, `take all`.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-28]]

<!-- connected:end -->
