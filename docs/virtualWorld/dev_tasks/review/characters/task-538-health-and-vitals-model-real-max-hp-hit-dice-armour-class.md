---
type: task
status: review
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

- [x] One resolver answers "the ceiling for this vital on this character", and
      every site in the table above reads it. No hardcoded `100` remains in an HP
      path.
- [x] A character with `Max_HP: 7` survives: `heal` never exceeds it,
      `adjust_vital` never exceeds it, decay never exceeds it, and the
      deserialisers in `engine/serialization.py` / `engine/serialization_template.py`
      preserve it.
- [x] `heal` clamps to `Max_HP` for HP and to `Max_{stat}` where that exists.
      **Regression test for the masked bug**, with a 7-HP fixture.
- [x] `heal` supports `target: "self" | "target"`, matching `apply_condition`.
- [x] HP regeneration stops at `Max_HP` for a character whose maximum is not 100
      (regression test for `tick_manager.py`).
- [x] `set_vital` and `modify_vital_max` exist as effects and are declared in
      `EFFECT_TYPES`; `modify_vital_max` raises the ceiling and does not
      retroactively change current HP unless asked.
- [x] `hit_dice` resolves `NdM+K` at hydrate time, and an explicit `Max_HP` in
      the same file wins over the formula — **decided and documented below**.
- [x] Every one of the 70 library characters and the item library still
      hydrate to their current vitals. This is the load-bearing regression.
- [x] `player.py`'s `Vitals & Needs (Max 100)` comment is corrected to
      describe the real model.
- [x] **The authoritative death path is decided and documented** — the `dead`
      condition — and the others are made to agree through one
      `world.kill_player`.
- [x] The health model is documented in code comments **and** in the user
      guide (`docs/virtualWorld/Characters/Vitals System.md`), not only here.
- [x] Full suite compared against a clean `master` worktree, by failure *name*.
      See "Verify" — the AGENTS.md baseline table is stale.

## The `Max_HP` vs `hit_dice` conflict rule — decided

**An explicit `Max_HP` wins over `hit_dice`.** A stat block that declares both
has already said what it wants, and a redundant declaration is not a
contradiction. Failing the load over it would be worse than honouring the
number.

This is also what makes the rule free: all 70 library characters set `Max_HP`
directly, so `hit_dice` is only ever a fallback and the whole library is
untouched by its introduction.

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `engine/vitals.py` — `ceiling`, `clamp_to_ceiling`, `parse_hit_dice`,
  `hit_dice_max`, `apply_hit_dice`, `DEFAULT_MAX_HP`, `DEFAULT_VITAL_MAX`,
  `BAND_VITAL_FLOOR`. **The rule now lives here and only here.**
- `engine/effect_handlers/vitals.py` — `_vital_ceiling` delegates to `ceiling`;
  `handle_heal` and `handle_adjust_vital` clamp through `clamp_to_ceiling`;
  new `handle_set_vital`, `handle_modify_vital_max`, shared `_effect_subject`.
- `engine/triggers/constants.py` — `set_vital`, `modify_vital_max` in
  `EFFECT_TYPES` and `SAFE_EFFECT_TYPES`.
- Rewired to the resolver: `engine/effects.py` (library hydrate),
  `engine/serialization.py`, `engine/serialization_template.py`,
  `vital_rates.py` (`change`), `engine/combat.py`, `engine/traits.py`
  (`scarred` threshold), `engine/tick_manager.py` (regen gate),
  `routes/player_ops.py` (the `Max_{vital}` convention), `player.py` (comment).
- `virtual_world_engine.py` — `kill_player`, the single death path.
- `routes/player_ops.py`, `engine/combat.py`, `engine/tick_manager.py` — the
  four lethal sites now route through it.
- `tools/gen_effect_templates.py` — `DEMO_PARAMS` + `LABELS` for the two new
  effects (the source of truth for the templates; the generator had been
  hand-patched for other effects instead).
- `docs/virtualWorld/Characters/Vitals System.md` — the user guide.
- `tests/test_health_model.py` — **new**, 43 tests.

### Two real bugs found on the way

1. **`data/library/characters/fluffy.json` has shipped with `Max_HP: 8`** — a
   sheep on a real stat block. So the `heal` bug was never hypothetical: healing
   Fluffy by 5 produced **13 HP on an 8-HP character**. Pinned by
   `test_the_library_already_ships_a_real_stat_block_on_a_non_100_scale`.
2. **`kill_player` swallowed an `AttributeError`.** Its first draft wrapped the
   lived-log write in `except Exception: pass`, and `player_manager.time_ticks`
   does not exist — the clock lives on the world. The death record was silently
   never written, which is precisely the failure the function existed to fix.
   Every `except` in it now logs instead of passing.

### Three decisions worth recording

1. **`ceiling` returns `inf` for Temperature**, not 100. Temperature is a body
   temperature in degrees; clamping it to a percentage was always a fiction, and
   its own band model (`cold_floor`/`normal`/`heat_ceiling`) is what decides
   lethality. This also unblocked reading the per-species temperature bands the
   task's §4 asked about.
2. **`hit_dice` averages half-up, not with integer division.** `2d6` is 7; a
   naive `(sides+1)//2` makes it 6, which would have made every generated stat
   block quietly wrong. `round()` is banker's rounding, so half-up is spelled out
   with `math.floor(x + 0.5)`.
3. **`CombatSystem` gets a `_game_state()` accessor.** Production passes the
   `VirtualWorld` as its `skills` parameter, but `tests/test_combat.py` hands
   over a `SkillSystem` monkey-patched with only the handful of methods the
   attack maths calls. Calling `kill_player` directly raised `AttributeError` on
   ordinary tests. The accessor walks to the world when there is one and the
   death branch keeps its inline fallback for the isolated harness — which is
   also why the old `drop_held_items` call was already wrapped in a bare
   `except`: it silently did nothing under the harness.

### Not done here, as the task specifies

- **Armour class** — split out by the task itself; it changes core resolution.
- **Per-region HP** — `engine/body_parts.py` `body_state` remains the natural
  home; a follow-up once the global model is settled.
- **`damage_type` / `resist` / `immunities` / `absorb` / `lifesteal` /
  `reflect_damage`** — stay in task-537; they need a scale to be a fraction of,
  which now exists.

### Verify

```
python -m pytest tests/test_health_model.py -q          # 43 passed
python -m pytest tests/test_health_model.py tests/test_health_model_fixes.py \
  tests/test_spell_effects.py tests/test_traits.py tests/test_combat.py \
  tests/test_conditions.py -q                          # 236 passed
```

**Full suite, compared by failure NAME against a clean `master` worktree** at
`7a44135` (the AGENTS.md table of 12 is stale; master measures 15 today):

```
15 failed, 6666 passed      mine
15 failed, ...              clean master
Compare-Object baseline mine  ->  (empty)
```

Zero difference in the failure set, so none of the 15 are mine. The 15 are
`test_character_identity` (2), `test_decay_rate_bake` (2),
`test_ownership` (4), `test_pines_slice` (1), `test_promotion` (1),
`test_scenario_data_integrity` (3), `test_scope_id_migration` (1),
`test_templates` (1 — `template_polymorph_target.json` is missing, the
documented baseline item).

`test_templates::test_generator_covers_every_effect_type` still fails for
exactly the reason it did before this task: five templates
(`polymorph_target`, `bind_companion`, `broadcast_emotion`,
`create_illusory_companion`, `reveal_hidden`) belong to other effects and were
already missing on master. The two templates this task needs **are** present,
with real demo params rather than the generator's empty `{}`.


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
