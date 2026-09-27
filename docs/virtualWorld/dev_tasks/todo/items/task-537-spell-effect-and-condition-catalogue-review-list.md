---
type: task
status: todo
area: items
priority: medium
---

# task-537: Spell effect and condition catalogue — review list

**Filed:** 2026-09-27
**Related:** task-391 (Lyrie's spellbook), task-534 (missing body reactions)
**Purpose:** a review list, not an implementation task.

## What this is

Every spell effect and condition the engine **does not have yet**, gathered from
tabletop RPGs, fantasy, sci-fi, modern, horror, and from the effects tools and
equipment imply but do not currently support.

**This is a menu to confirm or deny, not a build list.** Nothing here should be
implemented until someone has struck through the entries they do not want. An
engine with 400 speculative effect types is worse than one with 60 that all
work, because every one of them is a promise to an author.

**Reviewed 2026-09-27.** 73 entries confirmed, 23 carrying a recorded verdict.
Tick a box to **confirm** (build it). Blank means **deny**. Where the answer was
qualified — *maybe*, *not sure*, *don't add* — the reason is kept verbatim in a
`**Verdict:**` field so the nuance survives into the follow-up task.

## How to read the labels

These describe the *state of the engine*, not the reviewer's opinion, and are
independent of the checkbox.

- **[M] Missing** — no effect type or condition exists; needs new engine work.
- **[P] Partial** — something adjacent exists and can be composed, but the
 distinct mechanic is missing.
- **[A] Authorable today** — buildable from what exists, just never written.

### Corrections applied during the review

Four labels were wrong and have been fixed:

- `set_stat` / `modify_stat_max` were renamed **`set_vital`** /
 **`modify_vital_max`**. The engine says *vitals* throughout (`adjust_vital`,
 `p.vitals`); *stat* is a different, existing system (`Player.stats` =
 CHA/CON/DEX/INT/STR/WIS) and the two were conflated.
- `senses_restricted` and `stone_to`/`petrify` were labelled `[M]` but are
 **[A]** — `apply_condition` plus the existing `blind` / `deaf` / `petrified`
 conditions already cover them.
- `elemental_accumulate` was **denied and removed** as a bad entry:
 `adjust_environment` already does subtraction (it computes
 `current + int(params[key])` clamped to -50..100), so a negative value *is* the
 inverse.
- `light_source` is engine-side, not a trigger concern — `light_level` and
 `engine/lighting.py` own it, and `darkness_magic` plus `set_state` cover the
 trigger-level need.

---

## Baseline: what already exists

So the list below is a genuine gap list, not a guess.

**51 effect types** (`engine/triggers/constants.py` `EFFECT_TYPES`), including
`damage`, `heal`, `adjust_vital`, `drain`, `save`, `apply_condition`,
`remove_condition`, `apply_trait`, `apply_area_status`, `teleport`, `spawn_item`,
`spawn_character`, `set_hidden`, `adjust_uses`, `schedule_trigger`, `scry`,
`llm_respond`, `set_way_view`, `apply_area_status`, `set_weather`, `set_time`.

**5 spell effects added by task-391**: `polymorph_target`,
`create_illusory_companion`, `broadcast_emotion`, `bind_companion`,
`reveal_hidden`.

**47 trigger types** (`TRIGGER_TYPES`) — the full verb lifecycle including
`on_use_on`, `on_tick`, `on_delayed`, `on_state_enter/exit`, and the turn/moon
family (`on_turn_start`, `on_dawn`, `on_blood_moon`).

**38 conditions** in `data/library/conditions/`, including `aroused`, `bleeding`,
`blind`, `deaf`, `exhausted`, `frightened`, `goosebumps`, `itch`, `paralysed`,
`petrified`, `poisoned`, `prone`, `restrained`, `sensitized`, `sick`, `stunned`,
`suffocating`, `wet`.

**8 area statuses** in `engine/area_statuses.pyon_fire`, `smoke`, `flooded`,
`poison_gas`, `blessed`, `darkness_magic`.

**35 affect dimensions** (`engine/emotion.py` `baseline`) — the task-96
multi-dimensional map, which is far richer than the 7-value `set_emotion`.
> The emotion vocabulary is slated for a reword/expansion pass. Anything below
> that names a specific affect key is written against a moving target.

---

## A. Damage, defence and combat

- [x] **[M] `set_stat`** — set a vitals key to an absolute value, not a delta.
 `adjust_vital` only adds. Absent: "raise Temperature to exactly 37",
 "zero a limb's HP", "top a character up to a threshold". BUT should not be set_State, maybe set_vital?
- [x] **[M] `modify_stat_max`** — change `Max_HP`/`Max_Energy` itself. Absent:
 constitution buffs, armour that raises your ceiling, *vampiric* regen
 that expands it. sohuld again be vital, not stat
- [x] **[M] `damage_type`** — tag damage as fire/cold/poison/bludgeoning/
 psychic/radiant. Every `damage` is currently untyped, so resistances and
 immunities have nothing to key off. **This is the single highest-leverage
 gap in the list** — it unblocks resistances, immunities, weaknesses,
 element-specific gear and half-damage rules.
- [x] **[M] `resist` / `immunities`** — per-character incoming/outgoing
 modifiers, e.g. `resist: {cold: 0.5}`.
- [x] **[M] `absorb`** — a shield pool that intercepts damage before HP
 (barriers, wards, force fields). None of the task-391 spells needed it;
 most defensive ones will.
- [x] **[M] `knockback` / `push` / `pull`** — force a target a number of areas,
 a distance, or "toward/away from" a node. `teleport` is voluntary and
 absolute; nothing expresses *throwing someone*.
- [x] **[M] `grab` / `release` as effects** — the *actions* exist
 (`action_handlers.py`) but not as trigger effects, so a spell
 cannot grab.
- [x] **[M] `swap_places`** — exchange the actor's and a target's positions.
 Banishment, swaps and "you switch places with me" are a whole genre of
 their own.
- [x] **[M] `grapple_escape`** — contest a grab.
- [x] **[P] `reflect_damage`** — return a fraction of what you took. Absent as an
 effect; thorns/bodies-of-water as items would want it.
- [x] **[P] `lifesteal`** — heal in proportion to damage dealt. The vampire
 stat block needs it.
- [x] **[A] `damage` with `target: "target"`** — damage someone else. The
 existing `damage` effect should honour the `target` param the way
 `apply_condition` does (`conditions.py`). should have the options to target self, other, all in current area, all in areas within x hops, all in target area.

## B. Vitals, healing and death

- [x] **[M] `restore_uses` / durability** — *Mending Touch* had to be faked with
 `adjust_uses`, which silently no-ops on `uses: -1` items (indestructible).
 A real durability field is a schema change seeded here.
- [x] **[M] `revive`** — return a dead character to life with a cost. There is
 a `dead` condition and no way back from it.
- [ ] **Verdict:** maybe — **[M] `permanently_death`** — a `dead` that cannot be revoked, for vampire bite outcomes.
- [ ] **[M] `max_vital_floor` / ceiling modifiers** — *blood drain to zero*
 without killing.
- [x] **[P] `cure_all`** — clear every condition of a category (all injuries,
 all diseases) in one effect.
- [x] **[M] `disease`** — an actual disease entity with incubation, progression
 and a cure, rather than a condition with a timer. The plague miasma wants
 this.
- [ ] **Verdict:** maybe — **[A] `remove_trait` by category** — clear all traits in a category.

## C. Senses and perception

- [x] **[M] `grant_sense` / `blind_sense`** — darkvision, truesight, blindsight,
 tremorsense as a *parameter* on a character, not only as traits.
- [x] **[M] `detect`** — sense the nearest item/character/way of a given tag
 through walls. Detection spells are a whole class and have no effect.
- [x] **Verdict:** add, should already be possible via conditions — **[A] `senses_restricted`** — per-sense loss (`blind`/`deaf` exist as
 conditions, but not "your sense of direction is gone"). **Resolved during
 review:** the reviewer's note is right — this is just `apply_condition`
 with a condition per sense. Relabelled `[M]` → `[A]`; the work is authoring
 the conditions, not a new effect.
- [x] **[P] `illusion`** — a *perceived* change to a node that is not real
 (`append_description` can fake it; nothing can make everyone believe it).
- [x] **[M] `true_seeing`** — pierce illusions, see through walls briefly.
- [x] **[A] `scry` variants** — `scry` takes an area *name* only. A directional
 or nearest-matching form ("the nearest way out") would cover the whole
 scry-difficulty family.

## D. Movement, position and terrain

- [x] **Verdict:** needs additional work — **[M] `speed_modifier`** — slow, haste, slow movement. `dash` exists as an action; there is no persistent speed state. dev note: have been thinking aobut this, especially when considering riding a horse, a flying creature, driving a car, bike, or even a spaceship
- [x] **[M] `terrain_modify`** — make ground difficult/slippery/soft, or restore
 it. Mud, ice, marsh.
- [x] **[M] `create_terrain`** — a temporary feature (a bridge, a ramp, a
 frozen surface) that `spawn_area` cannot express.
- [x] **[M] `physics_impulse`** — throw something, with momentum. Relates to `knockback` above; the item nodes react to physics and this is the spell
 that would exploit it.
- [x] **[P] `leap`** — jump a specific distance, overriding the normal
 movement model.
- [x] **[M] `anchor`** — pin a character in place (hold person, paralysis as a
 spatial fact rather than a condition).
- [x] **[A] `teleport` with a chained way** — route through a way rather than to an absolute area. guess this is liek "use teleport west 3"?

## E. Time, duration and scheduling

- [x] **[M] `delay_effect`** — run these effects N turns later on a *different* node than the one casting. `schedule_trigger` fires on the casting node, so "the arrow arrives three turns later" is inexpressible.
- [x] **[M] `repeat_effect`** — fire these effects every N ticks for a duration.
 Poisonous clouds, pulsing auras, regen-over-time. `on_tick` + `adjust_uses`
 is the current workaround and it is clumsy.
- [ ] **Verdict:** maybe — **[M] `time_freeze`** — an area where turns do not pass. Absurd and occasionally necessary.
- [x] **[M] `age_effect`** — age a target by N years, or a year per cast. but might require the graph editor character model first
- [ ] **Verdict:** maybe — **[M] `reversible_duration`** — an effect that can be cancelled before it expires (dispel magic). Every task-391 duration is unconditional.
- [ ] **Verdict:** mabybe — **[P] `hasten` / `slow_time`** — relative rather than absolute rate
 change.
- [x] **[A] `set_time` / `set_date` with a relative offset** — "+1 hour" rather
 than an absolute value.

## F. Transformation and the body

- [x] **[M] `shapechange`** — assume a *different character template* wholesale, as distinct from task-391's `polymorph_target` which swaps a node's presentation. True lycanthropy, possession, a dragon form.
- [x] **[M] `size_change`** — grow/shrink, with mass and reach consequences.
- [x] **[M] `limb_disable`** — sever a limb; needs a body-part model.
- [ ] **Verdict:** isa condition — **[A] `stone_to` / `petrify` as a state change** — `petrified` exists as a
 condition but nothing turns a character into scenery. **Relabelled `[P]` →
 `[A]` during review:** the reviewer's note is right, `apply_condition:
 petrified` already does it.
- [ ] **Verdict:** maybe — **[M] `secrete` / `exude`** — poison spray, gas, ink.
- [ ] **Verdict:** maybe — **[M] `venom`** — apply a condition on successful damage rather than requiring a separate effect.
- [x] **[M] `disease_resist` / `curse`** — a long-lived debuff that is not a condition and cannot be `remove_condition`'d away.
- [x] **[A] `set_state` on a target** — "the target is now `on_fire`" rather than only on self. Currently `_resolve_effect_target` mostly resolves to the item itself.

## G. Social, emotion and mind

- [x] **[M] `mind_affect`** — compulsion, charm, suggestion, dominate. The condition vocabulary has `charmed`, but there is no effect that *applies* intent to a target's decisions. might be able to use the nudge feature?
- [ ] **Verdict:** maybe — **[M] `reaction_trigger`** — bind a trigger to a character, not to a node: "when I am attacked, cast this". This is how reactions should work, and it also gives task-352's action economy a real place to hang a reaction. i feel liek reactins should be hadnled like in baldurs gate. possibly more of a behaviour than tirgger, but migh also be usefull for traps so okay lets keep it in there for triggers to
- [x] **[M] `memory_wipe`** — remove a specific memory, not just suppress it. but requires strit criterias, like tags, items, charcters etc. 
- [x] **[M] `memory_inject_false`** — plant a memory that did not happen. The memory system is rich enough to want this and it is a horror staple.
- [x] **[M] `insight`** — read a target's disposition, current emotion or relationship to you. Conversational detection magic.
- [x] **[M] `persuade` / `intimidate` / `sway_checks`** — social resolution as a first-class effect. The relationship system exists; nothing moves it deliberately. possibly not on triggers but as first class action?
- [x] **[M] `speech_style`** — force a character to speak in a register (charm, truth, compulsion), the inverse of task-391's `llm_respond`.
- [ ] **Verdict:** maybe — **[P] `fear_aura` / `presence`** — a persistent area effect that moves affect each turn. `broadcast_emotion` is one-shot.
- [x] **[M] `language`** — grant or remove a language, and make speaking it actually gated.
- [ ] **Verdict:** maybe — **[A] `emotion` set vs spike** — `broadcast_emotion` spikes the affect map; there is no effect that sets a character's canonical `emotion` string outright. emotins are in need of a bigger rework.

## H. Items, equipment and economy

This is the section the tools and equipment imply most strongly.

- [x] **[M] `modify_property`** — change one property on a target item arbitrarily (`+2 damage`, `+10 capacity`, `change its material`). The workhorse for cursed and blessed gear.
- [x] **[M] `enchant_item`** — a persistent, removable property change with conditions (`while carried`, `while lit`, `at night`).
- [x] **[M] `curse_item`** — the inverse, and a genre in itself.
- [ ] **Verdict:** maybe — **[M] `attune`** — bind an item to a character so nobody else can use it.
- [ ] **Verdict:** not sure — **[M] `set_owner`** — assign ownership independently of attunement.
- [ ] **Verdict:** maybe? — **[M] `bind_action`** — make an item perform an action on use (the `bind`/`enchant` action exists with `SAFE_EFFECT_TYPES`; this generalises it to items that are not spells).
- [x] **[M] `randomize_property` / `reroll`** — enchant a weapon so it gets a random bonus, reroll a magic item. Enchanted-weapon loot needs it.
- [x] **[M] `item_merge` / `item_split`** — combine materials, divide a stack.
- [x] **[M] `decay_item`** — accelerate rust, rot, souring, corrosion.
- [x] **[M] `transmute_item`** — turn one item into another *by library id*, related to task-391's `polymorph_target` but for a permanent swap and a different template. The distinction (temporary presentation change vs permanent identity change) should be deliberate.
- [ ] **Verdict:** maybe — **[M] `container_pressure` / bulk** — weight/volume mechanics.
- [x] **[P] `repair_item`** — *Mending Touch*'s original proposal. Real durability first, then this becomes a thin wrapper.
- [x] **[A] `set_uses`** — absolute use count, to complement `adjust_uses`.
- [x] **[A] `grip` / `throw`** — a `throw` action exists; no effect form. tldr, throw = roll a attack and damag,e then weapon is AT the target. lik how drop places a item AT the dropper.
- [x] **[M] `craft_from`** — build an item out of others (the `combine` action exists; as an effect it would let recipes be spells).

## I. World and environment

- [x] **[M] `weather_local`** — weather for one area, not the whole world. `set_weather` is global and one player's rainstorm is everyone's.
- [x] **[M] `terrain_convert`** — turn a node into another type (wall↔door, floor↔water). `spawn_way`/`spawn_area` are additive; nothing transforms.
- [ ] **Verdict:** maybe — **[M] `collapse`** — destroy a structure; a siege genre in one word.
- [ ] **Verdict:** dont add, is same as spawn — **[M] `raise_from_below`** — walls, doors and creatures rising from the ground. Dungeon geometry changing mid-fight.
- [ ] **Verdict:** not sure i understand this one — **[M] `elemental_accumulate`** — the reverse of `adjust_environment`, to undo a cast.
 **Resolved during review — removed, and the reviewer's confusion was the
 signal.** The entry was wrong: `adjust_environment` already does
 subtraction. It computes `current + int(params[key])` clamped to
 -50..100 (`engine/effect_handlers/environment.py`), so a negative
 value *is* the inverse. No new effect needed.
- [x] **[M] `time_of_day_lock`** — hold dawn, or make it permanent night.
- [x] **[M] `sound_propagate`** — a sound at a point rather than an area (`broadcast_emotion` has radius, nothing has range-and-direction).
- [x] **[M] `darkness` / `light_source`** as effects** — `darkness_magic` is an area status; no effect creates a portable light or snuffs one. but light source is engine side, not a trigger
- [ ] **[A] `forecast_override`** — exists; note that a *spell* forecast is currently indistinguishable from a GM one.

## J. Companions, summons and entities

- [x] **[M] `summon_creature`** — spawn from a *template* with a count (`3 wolves`), opposed to task-391's single named companion.
- [x] **[M] `dismiss_summon`** — end a binding early. There is no dispel for
 anything task-391 added.
- [x] **[M] `command_entity`** — issue an order to a bound companion. The familiar follows you; nothing makes it *act*.
- [x] **[M] `entity_aggro`** — set a summoned thing's disposition toward a target.
- [x] **[M] `possess`** — take control of a character. The most requested magic trope and entirely absent.
- [ ] **Verdict:** dont add — **[M] `merge` / `split_creature`** — combine two summons into one boss.
- [x] **[P] `charm_person`** — non-lethal `mind_affect` scoped to one target.
- [x] **[A] `despawn`** — remove a spawned node or character deliberately. `engine/companions._despawn_character` does this for conjurations; nothing exposes it to authors.

## K. Information and knowledge

- [x] **[M] `reveal_property`** — show a hidden stat on a node (its alignment, its true name, whether it is cursed) for a duration.
- [x] **[M] `lore`** — grant knowledge as a fact the character can act on, as distinct from a `surface_memory` recollection.
- [x] **[M] `identify`** — name an unknown item or person permanently. The name system (`first_sighting`, `knows_name`) has no effect that writes to it.
- [x] **Verdict:** add, tie to the narration system, systemically detemrine a boolean reply, or ask player/GM or llm — **[M] `divine`** — ask a question, get a yes/no with a truthfulness
 guarantee or a cost. Paladin and detective magic both want this.
- [ ] **Verdict:** kind of have, via record area or data effects? — **[M] `record` / `replay`** — capture an event and re-narrate it later.
 Excellent for memory spells and cheap to build on the trace log.
- [x] **[A] `append_description` with a duration** — a timed lore overlay; a poor-man's `identify`.

## L. Conditions worth adding

Grouped by what they would be *for*, since most are one-line additions to
`data/library/conditions/`.

> **This section is load-bearing for D and G.** `anchor` has nothing to apply
> without `rooted`; `mind_affect` has nothing without `dominated`/`enchanted`;
> `speech_style` has nothing without `silenced`. Deciding L as the vocabulary
> the rest of the list borrows from is cheaper than approving those effects and
> then discovering they have nowhere to land.

- **Sensory** — `[add ]` `dazed` (actions but not reactions), `[ ]` `deafened` (partial, vs `deaf`), `[ ]` `blinded` (partial), `[ ]` `silenced` (cannot speak), `[ ]` `hallucinating` exists.
- **Motor** — `[ ]` `crippled` (speed), `[ ]` `trembling`, `[ ]` `rooted` (cannot move, can act), `[ ]` `staggered`, `[ ]` `prone` exists.
- **Vital** — `[ ]` `bleeding` exists — add `[ ]` `haemorrhaging` for a bleed that will not stop without treatment, `[ ]` `fractured`, `[ ]` `infection`,
 `[ ]` `malnourished`, `[ ]` `dehydrated` (as distinct from `Thirst` hitting zero).
- **Mental** — `[ ]` `delirious`, `[ ]` `nightmare`, `[ ]` `enchanted`, `[ ]` `dominated`, `[ ]` `cowardly`, `[ ]` `enraging`, `[ ]` `confused`.
- **Social** — `[ ]` `infatuated`, `[ ]` `terrified`, `[ ]` `resentful` (as a state, not an affect axis), `[ ]` `silenced`.
- **Magical** — `[ ]` `blessed`, `[ ]` `cursed`, `[ ]` `banned` (from a particular school), `[ ]` `marked` (targeted by a hunter), `[ ]` `hunted`.
- **Resource** — `[ ]` `exhausted` exists — add `[ ]` `spent` for one-shot abilities, `[ ]` `focused`, `[ ]` `overextended` (from channelling).

---

## M. Hit points, armour class and creature scale

Raised by the reviewer on 2026-09-27: **"we need to be able to set HP and Max_HP
more easily — 100 being default is not quite correct, especially in a D&D-like
basis."** Confirmed, and it is bigger than two effects.

### The evidence

The 5e monster PDF (`~/Downloads/Monsters for Dungeons & Dragons 5e - D&D Beyond.pdf`,
17 pages) gives the range the engine currently cannot express:

| | Values in the PDF |
|---|---|
| HP |
| Hit dice | `2d6`, `3d6`, `2d8+2`, `5d8+10`, `6d6`, `6d8+12`, `7d8+14` |
| Armour Class |

A goblin is **7 HP**. The engine's floor is 100. So a 5e stat block is not merely
hard to express, it is wrong by more than an order of magnitude at the low end —
and a 100-HP goblin takes 14 sword hits to down.

### What is missing

- [x] **[M] `set_vital`** — set a vitals key to an absolute value. `adjust_vital`
 only adds. The engine's own naming is *vitals*, not *stats*
 (`Player.stats` is CHA/CON/DEX/INT/STR/WIS — a different system).
 *(Was `set_stat`; renamed during the review.)*
- [x] **[M] `modify_vital_max`** — change `Max_HP`/`Max_Energy` itself. Absent:
 constitution buffs, armour that raises the ceiling, *vampiric* regen that
 expands it. **This is the keystone of the section**: raising a character's
 maximum is a core 5e mechanic and the reason the effect is wanted at all.
 *(Was `modify_stat_max`; renamed during the review.)*
- [x] **[M] `hit_dice`** — author HP as a *formula* rather than a number
 (`"hit_dice": "7d8+14"`), rolled or averaged at hydrate time. This is the
 D&D-native way and it is what makes creatures scale without re-authoring
 every stat block. Needs a dice-expression parser; the engine already has
 `skills.roll_dice(count, sides, mod)`.
- [x] **[M] `armour_class`** — a defence stat that does not exist anywhere. Combat
 is currently `d20 + STR + mod` vs `d20 + DEX` (`engine/combat.py`),
 so AC 13–18 from the PDF is inexpressible. Large: it changes the core
 resolution, so it is its own task rather than a line item here.
- [x] **[M] `max_vital_floor`** — a damage floor below which a vital cannot be
 driven ("blood drain to zero without killing"). Previously left blank; now
 confirmed because it is entangled with `resist`/`immunities` — without it,
 denying a kill is inexpressible and resistance has nothing to clamp.
 **Do not approve `resist` without this.**

### A latent bug this work activates

`handle_heal` (`engine/effect_handlers/vitals.py-137`) clamps to a
**hardcoded 100** and ignores `Max_HP`, while `handle_adjust_vital`
(`vitals.py`) correctly clamps HP to `Max_HP``python
# handle_heal — wrong for any Max_HP that is not 100
vitals[stat] = min(100, vitals.get(stat, 100) + amount)
```

Healing a 7-HP goblin by 5 therefore produces **12 HP, over its maximum**. This is
invisible today *only because `Max_HP` is always 100* — the bug is masked by the
very thing this section removes. Fix `heal` to clamp to `Max_HP` for HP (and
`Max_{stat}` where that exists) in the same change that makes `Max_HP` authorable,
or the first real stat block will find it.

The `Max_HP` default of 100 is also duplicated in at least nine places —
`player.py`, `engine/effects.py`, `engine/serialization.py`,
`engine/serialization_template.py`, `engine/combat.py`,
`vital_rates.py`, `engine/traits.py`, `routes/player_ops.py`, `engine/effect_handlers/vitals.py`. All of them need to agree, and
a single source of truth for "the default" is worth more than the default itself.

---

- Implementing anything. This is a list.
- Porting a ruleset wholesale. These are the *mechanics other systems imply*,
 not their balance or their numbers.
- Reactions as a turn-economy feature — that is task-352, and
 `reaction_trigger` here is the engine hook it would need.

## Notes for whoever works this list

- **`damage_type` first.** It is a small schema change with the largest
 downstream unlock: resistances, immunities, elemental gear, and half the
 defensive entries above depend on it.
- **The emotion vocabulary is moving.** Anything naming a specific affect key
 (section G) will need revisiting after the planned reword.
- **Prefer composition over new types.** `apply_area_status` + a condition
 covers a surprising amount of "new" effect. Where a proposed entry can be
 written as a combination, say so in the entry rather than adding a type.
- **Durability is a schema change, not an effect.** `adjust_uses` silently
  no-ops on `uses: -1`, which makes *Mending Touch* a no-op on a growing list of
  library items. That is a data-model decision and should be taken on its own.
- **Decided 2026-09-27: soak telemetry carries `why`, reusing this vocabulary, with
  one structural exclusion.** Both the per-character `lived_log` and the soak's
  run-owned telemetry record "Jake moved to the Storehouse" and both need to say
  *why* — the two use the field for different purposes, but the vocabulary can be
  shared. In the `lived_log` `why` is diagnostic prose, so a reader or an LLM can
  see whether a hungry character was driven by fear, a plan, or bad luck. In
  telemetry `why` **is** the measurement: the question a soak answers is "which of
  the background rules did the most work", and that can only be answered by
  counting `why` values. Without it telemetry reports "Jake moved 47 times",
  which is not a finding.
  The rules for telemetry: reuse the `needs:` / `goal:` / `plan:` / `social:` /
  `threat:` / `order:` / `env:` prefixes, keep them **closed and prefix-groupable**
  so `plan:*` buckets for a bar chart, and **exclude `llm:`** — a soak makes no LLM
  calls by construction (`engine/soak_runner.py` states it, and `background_all`
  forces every character to `simulation_mode = "background"`), so `llm:` would be a
  permanently empty category that invites "why is this always zero?". Excluding it
  is structural, not a preference, and it makes reuse nearly free: telemetry uses a
  strict subset of a vocabulary that already exists.
  This was decided **before** capture on purpose. Building the capture and the
  dashboard first means inventing tags as needed — `hunger`, `needs:hunger`,
  `need_hunger` — and then every count splits three ways, with no way to tell a
  data problem from a vocabulary problem. Retrofitting costs a rewrite of every
  recorded run, which are the expensive artifact.
