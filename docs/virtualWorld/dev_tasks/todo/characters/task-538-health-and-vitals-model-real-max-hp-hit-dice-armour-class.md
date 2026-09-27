---
type: task
status: todo
area: characters
priority: high
---

# task-538: Health and vitals model — real Max_HP, hit dice, armour class

**Filed:** 2026-09-27
**Origin:** raised while reviewing task-537 (spell effect catalogue) — *"we need to
be able to set HP and Max HP more easily, 100 being default is not quite correct,
especially in a D&D-like basis."*
**Related:** task-537 §M, task-352 (action economy), task-213 (traits)

## Problem

**The engine has no health model — it has a 100.** `Max_HP` is the only vital
with a maximum, and its default is the literal `100`, hardcoded in at least ten
places. That single assumption is load-bearing for death, regeneration, healing
and hydration, and it is wrong by more than an order of magnitude for anything
built on a tabletop basis.

The evidence, from the 5e monster PDF at
`~/Downloads/Monsters for Dungeons & Dragons (D&D) Fifth Edition (5e) - D&D Beyond.pdf`
(17 pages, text extracted with `pypdf`):

| | Values in the PDF |
|---|---|
| HP |
| Hit dice | `2d6`, `3d6`, `2d8+2`, `5d8+10`, `6d6`, `6d8+12`, `7d8+14` |
| Armour Class |

A goblin is **7 HP**. The engine's floor is 100, so a 5e stat block is not merely
hard to express — it is wrong by more than 10× at the low end, and a 100-HP goblin
takes fourteen sword hits to down.

## Scoping notes (2026-09-27, measured)

### 1. The 100 is hardcoded in at least ten places

| Location | Use |
|----------|-----|
| `player.py` | the default itself: `"HP": 100, "Max_HP": 100` |
| `engine/effects.py` | hydrate: `if "Max_HP" not in p.vitals: p.vitals["Max_HP"] = 100` |
| `engine/serialization.py` | load: same default, then clamp HP to Max_HP |
| `engine/serialization_template.py` | same again |
| `engine/effect_handlers/vitals.py` | `adjust_vital`'s HP cap (correct — uses Max_HP) |
| `engine/effect_handlers/vitals.py-137` | **`heal`'s cap (hardcoded 100 — see below)** |
| `vital_rates.py` | `cap = vitals.get("Max_HP", 100) if stat == "HP" else 100` |
| `engine/combat.py` | `hp_max = target.vitals.get("Max_HP", 100) or 100` |
| `engine/traits.py` | `max_hp = vitals.get("Max_HP", 100)` |
| `routes/player_ops.py` | the `Max_{vital}` lookup convention |
| `engine/tick_manager.py` | **HP regen gate: `p.vitals.get("HP", 100) < 100`** |

`player.py` labels the whole block `Vitals & Needs (Max 100)`, so the
assumption is documented as a design decision rather than an oversight.

**A single source of truth is worth more than the default itself.** Every one of
these should read one constant or, better, one resolver that answers "what is the
ceiling for this vital on this character".

### 2. `heal` ignores `Max_HP` — a live bug, currently masked

`engine/effect_handlers/vitals.py``python
# handle_heal (:129-131) — hardcoded 100
vitals[stat] = min(100, vitals.get(stat, 100) + amount)

# handle_adjust_vital (:175-178) — correct, uses Max_HP
player.vitals[key] = max(0, min(100, player.vitals[key] + amount))
if key == "HP":
 max_hp = player.vitals.get("Max_HP", 100)
 player.vitals[key] = max(0, min(max_hp, player.vitals[key]))
```

Healing a 7-HP goblin by 5 with `heal` yields **12 HP, over its maximum**. This
is invisible today *only because `Max_HP` is always 100* — the bug is masked by
the exact thing this task removes. **Fix it in the same change that makes
`Max_HP` authorable**, or the first real stat block will find it.

`heal` also does not support a `target` param at all ( uses
`game_state.player` directly), unlike `apply_condition`
(`engine/effect_handlers/conditions.py`) and `adjust_vital` .

### 3. HP regeneration is gated on a literal 100

`engine/tick_manager.py``python
if (p.vitals.get("Energy", 0) > 25 and p.vitals.get("Hunger", 0) > 25 and
 p.vitals.get("Thirst", 0) > 25 and p.vitals.get("Sanity", 0) > 25 and
 p.vitals.get("HP", 100) < 100 and 35 <= p.vitals.get("Temperature", 37) <= 39):
 regen_mult = float(TraitSystem.get_hp_regen_multiplier(p) or 1.0)
 self._decay(p, "HP", HP_REGEN * max(1.0, regen_mult))
```

The gate is "HP is below 100", i.e. "HP is below maximum". For a 7-HP goblin
that is **always true**, so a goblin regenerates HP every single turn forever and
can never be finished off by attrition. The intent is obviously
`HP < Max_HP`; it is written as the literal.

### 4. There are at least three unrelated death paths

- **HP** — `tick_manager.py` (`HP <= 0`), and for temperature
 bands (`cold_critical` / `heat_critical`).
- **Exhaustion** — `tick_manager.pyEnergy <= 0` → `unconscious`, drops
 held items, increments `exhaustion_count`; at 3 → `state = "dead"`, spawns a
 body item. This **bypasses HP entirely** and is a separate counter from damage.
- **Conditions** — `dead` as a condition (`data/library/conditions/dead.json`),
 distinct from `p.state == "dead"`.

A character can be `state == "dead"` with full HP, or at `HP <= 0` without being
`dead`. Which one is authoritative is currently undefined.

### 5. Vitals are not one scale — there are four models

- **0-100 clamped** — HP, Energy, Hunger, Thirst, Hygiene, Social, Bladder,
 Sanity, Entertainment, and `Mana` when the `magic` tag is present
 (`player.py` `sync_vitals_with_tags`).
- **Band-based** — `Temperature` is anatomical (default `37.0`,
 `player.py`) and has its own drift model with `cold_floor` / `normal` /
 `heat_ceiling` and its own death path (`tick_manager.py`). It is
 explicitly excluded from decay at (`if stat ... and stat != "Temperature"`).
- **Per-region** — `engine/body_parts.py` `BODY_REGIONS` with
 `player.body_state` (`player.py`, task-253), so localised injury state
 already exists and is the natural home for localised HP.
- **Conditions** — `bleeding`, `poisoned`, `hypothermia`, `sick` are a parallel
 damage model that does not go through `HP` at all.

Putting a 7-point HP and a 37-degree body temperature and a 100-point Energy on
one undifferentiated "vitals" dict is the root of most of the awkwardness. This
does not have to be solved to ship a goblin, but it should be *decided* rather
than discovered again per stat block.

### 6. `Max_` is a convention with one instance

`routes/player_ops.py` looks up `f"Max_{vital_name}"`, and
`engine/serialization.py` aliases only `max_hp` → `Max_HP` and
`max_mp` → `Max_Mana`. So the convention exists, is half-implemented, and is
already wrong for any vital that is not a percentage.

### 7. Armour class does not exist

Combat is `d20 + STR + mod` versus `d20 + DEX`
(`engine/combat.py`, traced at ). AC 13–18 from the PDF is
inexpressible. `defense` exists on **items** (`data/library/items/*.json`) and is
an unrelated concept — an item's own protection, not a worn stat.

This is the one item here that changes core resolution, so it is called out as
its own follow-up rather than folded in here.

## Design

**`Max_HP` becomes data, not a constant.** The minimum viable change is:

1. A single resolver for "the ceiling of vital V on character P", replacing the
 ten hardcoded sites. It should understand: an authored `Max_{V}` if present,
 the vital's natural scale otherwise, and never silently fall back to 100 for
 HP.
2. `set_vital` / `modify_vital_max` effects (task-537 §M), so a spell or trait can
 raise a maximum — which is the reason the effect is wanted at all.
3. `heal` and `adjust_vital` agreeing on the cap, and `heal` growing a `target`
 param.
4. The regen gate at `tick_manager.py` reading `Max_HP`.

**Hit dice are the scalable half.** `"hit_dice": "7d8+14"` derives `Max_HP` at
hydrate time, so a family of creatures can be authored by formula and rescaled
without hand-writing every stat block. `skills.roll_dice(count, sides, mod)`
already exists (`engine/combat.py`); what is needed is a dice-expression
parser and a decision about roll-versus-average at load time (average is almost
certainly right for a *bestiary* and wrong for a *character who rolls up*).

**Keep `Max_HP` authorable directly** as well as by formula. The ~525 existing
library items and 68 characters predate any hit-dice concept and must keep
working unchanged; a stat block may want either, and both authoring styles
should coexist.

## Acceptance criteria

- [ ] One resolver answers "the ceiling for this vital on this character", and
 every site in the table above reads it. No hardcoded `100` remains in an HP
 path.
- [ ] A character with `Max_HP: 7` survives: `heal` never exceeds it,
 `adjust_vital` never exceeds it, decay never exceeds it, and the
 deserialisers in `engine/serialization.py` / `engine/serialization_template.py`
 preserve it.
- [ ] `heal` clamps to `Max_HP` for HP and to `Max_{stat}` where that exists.
 **Regression test for the masked bug**, with a 7-HP fixture.
- [ ] `heal` supports `target: "self" | "target"`, matching `apply_condition`.
- [ ] HP regeneration stops at `Max_HP` for a character whose maximum is not 100
 (regression test for `tick_manager.py`).
- [ ] `set_vital` and `modify_vital_max` exist as effects and are declared in
 `EFFECT_TYPES`; `modify_vital_max` raises the ceiling and does not
 retroactively change current HP unless asked.
- [ ] `hit_dice` resolves `NdM+K` at hydrate time, and an explicit `Max_HP` in
 the same file wins over the formula (or the conflict is an error — decide
 and document which).
- [ ] Every one of the 68 library characters and 525 library items still
 hydrate to their current vitals. This is the load-bearing regression: the
 change must be backward compatible.
- [ ] `player.py`'s `Vitals & Needs (Max 100)` comment is corrected to
 describe the real model.
- [ ] **Decide and document which death path is authoritative** — `p.state ==
 "dead"`, the `dead` condition, `HP <= 0`, or exhaustion count — and make
 the others agree. Right now a character can be dead with full HP.
- [ ] Per the standing rule, the health model is documented in code comments and
 the user guide / technical docs, not only here. The 100-default and the
 regen gate are exactly the kind of thing that has been misunderstood before.
- [ ] Full suite compared against the ~60 failed / 3953 passed baseline.

## Split out rather than folded in

- **Armour class** — its own task. It changes core resolution, so it does not
 belong in a change that is otherwise about scale hygiene.
- **Per-region HP** — `engine/body_parts.py` already carries `body_state`; making
 that a *vital* with its own ceiling is a natural follow-up once the global
 model is settled.
- **The remaining task-537 §M entries** (`damage_type`, `resist`/`immunities`,
 `max_vital_floor`, `absorb`, `lifesteal`, `reflect_damage`) stay in task-537.
 They are all downstream of this and meaningless before it: resistance needs a
 ceiling to clamp against, and `damage_type` needs a scale to be a fraction of.

## Non-goals

- Porting 5e as a ruleset. These are the *mechanics a stat block implies*, not
 its balance, its numbers, or its action economy.
- Challenge Rating, proficiency bonus, or a class/level system. `hit_dice` is the
 one piece of that which pays for itself here.
- Reworking `Energy`, `Sanity`, `Entertainment` or the drive inversion
 (task-337). They work; they are only sharing a dict with HP.
- Retro-fitting all 68 library characters to hit dice.

## Related

- task-537 §M — the spell-effect entries this came out of (`set_vital`,
 `modify_vital_max`, `hit_dice`, `armour_class`, `max_vital_floor`).
- task-352 — action economy; `exhaustion_count` and the three-strike collapse at
 `tick_manager.py` is a turn-economy interaction, not a health one.
- task-213 — mature traits; `quick_recovery` and `sensory_memory` already sit in
 this area and are the precedent for `modify_vital_max` as an effect.
- `engine/body_parts.py` — task-253's per-region state, the future home of
 localised HP.
