---
type: doc
tags: [system/characters]
---

# Vitals System

Vitals are numeric meters that track a character's physical and mental state. Most are 0-100 percentages; three are not, and that is the model rather than an oversight. They decay over time and must be maintained through actions like eating, drinking, resting, and socializing.

> **All rates on this page are per in-game MINUTE, not per tick.** The engine
> scales them by the tick's length (`world.time_per_tick_minutes`, see
> `vital_rates.tick_minutes`), so a 15-minute tick applies fifteen minutes of
> decay. The table below used to read "decay per tick" with whole numbers, from
> before the 2026-09 per-minute recalibration; a scenario that bakes rates in the
> old per-tick scale is caught by `tests/test_decay_rate_bake.py`.

## HP is on its own scale (task-538)

**HP is the only vital whose maximum is authorable, and 100 is its _default_,
not its scale.** Before task-538 that `100` was written out as a literal in
about ten places — `player.py`, `engine/effects.py`, both deserialisers, both
vital effect handlers, `vital_rates.change`, `engine/combat.py`,
`engine/traits.py` and the regeneration gate in `engine/tick_manager.py`. The
literal was harmless only because `Max_HP` was itself always 100, and that is
what hid two live bugs:

- `heal` clamped to 100, so healing a character by 5 could take it *above* its
  own maximum. `data/library/characters/fluffy.json` (a sheep) has shipped with
  `Max_HP: 8` for months, so this was a bug in **shipped data**, not a
  hypothetical one.
- The regeneration gate read "HP < 100", i.e. "HP < maximum". For a
  character whose maximum is 7 that is permanently true, so it regenerated
  every turn and could never be finished off by attrition.

There is now **one** function that answers the question:

```python
from engine.vitals import ceiling
ceiling(player.vitals, "HP")     # -> the character's own maximum
```

`engine.vitals.ceiling` is the only place the rule lives. Every reader asks it.
**Never write the literal 100 in an HP path** — that is the mistake the task
existed to remove, and `tests/test_health_model.py::
test_no_module_hardcodes_the_hp_ceiling` scans the modules the task named and
fails if one comes back (comments and docstrings are stripped first, so prose
about the old literal is fine).

### The three scales

| Scale | Vitals | Rule |
|-------|--------|------|
| Percentage, 0-100 | Energy, Hygiene, Social, Sanity, Entertainment, Comfort, Mana, Arousal, Stimulation, Pleasure | `ceiling` returns 100 |
| Drive, fills toward 100 | Hunger, Thirst, Bladder | 100 is the *bad* end |
| **Own scale** | **HP** | authored `Max_HP`, else 100 |
| Band, anatomical | Temperature | ~37 °C; `ceiling` returns infinity and the tick manager's `cold_floor`/`normal`/`heat_ceiling` bands decide what is lethal |

### Authoring a real maximum

Two ways, both first-class, and they coexist:

```jsonc
{ "name": "Goblin", "vitals": { "HP": 7, "Max_HP": 7 } }
```

```jsonc
// the scalable half: a family of creatures authored by formula
{ "name": "Ancient Black Dragon", "hit_dice": "21d12+112" }
```

`hit_dice` resolves `NdM+K` at load time in `engine/vitals.hit_dice_max`:

- **average** is the default and the right answer for a *bestiary*: `2d6` is 7,
  `7d8+14` is 46. It is the mean rounded half-up, so `2d6` is 7 and not the 6
  integer division gives.
- **roll** is for a character that rolls up at creation
  (`"hit_dice_mode": "roll"`). A bestiary must not be `roll`, or a creature's
  health changes every time a save is loaded.
- A bare `"d8"` means 1d8. An unreadable expression resolves to nothing at all
  rather than to 0 HP — a typo in a stat block should be visible.
- The result is floored at 1: a character with no maximum at all is a much
  worse failure mode than one point of health.

**An explicit `Max_HP` wins over `hit_dice`.** That is the decided conflict
rule, and it is what keeps the whole library backward compatible: every one of
the 70 library characters sets `Max_HP` directly, so `hit_dice` is only ever a
fallback. A stat block listing both is redundant, not contradictory, and failing
the load over it would be worse than honouring the number.

### The `Max_` convention

`Max_{Vital}` is a general convention, not an HP special case: `ceiling` looks
for `f"Max_{stat}"` first, so `Max_Mana` works exactly the same way.

## Vitals Reference

| Vital | Default | Min | Max | Decay/min | Critical at 0 |
|-------|---------|-----|-----|------------|----------------|
| `HP` | 100 | 0 | **`Max_HP`** (or `hit_dice`) | 0 (damage only) | Death |
| `Max_HP` | 100 | — | — | — | — |
| `Energy` | 100 | 0 | 100 | 0.104 | Unconscious → Death (after 3x) |
| `Hunger` | 100 | 0 | 100 | 0.0034 | HP damage (starvation) |
| `Thirst` | 100 | 0 | 100 | 0.0250 | HP damage (dehydration) |
| `Hygiene` | 100 | 0 | 100 | 0.020 | — |
| `Social` | 100 | 0 | 100 | 0.020 | Sanity penalty |
| `Bladder` | 0 | 0 | 100 | — (fills at 0.42/min) | Hygiene penalty crossing 60 |
| `Sanity` | 100 | 0 | 100 | 0.005 | **never damages HP** — see below |
| `Entertainment` | 100 | 0 | 100 | 0.030 | Sanity penalty |
| `Temperature` | 37.0 | ~25 | ~45 | — | HP/Energy damage at extremes |

`vital_rates.BASELINE_DECAY` is the authority. From a full meter: Hunger reaches
the starvation edge in ~3 weeks, Thirst the dehydration edge in ~3 days, Energy
empties over a ~16h waking day, and Social/Hygiene/Entertainment run on a ~1-2 day
cycle.

## Writing a vital from an effect

Four effects touch vitals, and all four clamp through
`engine.vitals.clamp_to_ceiling`, so they cannot disagree about where the top is:

| Effect | What it does |
|--------|--------------|
| `adjust_vital` | `{stat, amount, target}` — moves the meter, clamped |
| `set_vital` | `{stat, value, target}` — sets it to an exact value, clamped |
| `modify_vital_max` | `{stat, amount, target, scale_current}` — moves the **ceiling** |
| `heal` | `{stat, amount, target}` — adds, clamped (and reports what was *actually* restored) |

All four accept `target: "self"` (default) or a character name, resolved
case-insensitively.

`modify_vital_max` is the reason a maximum wants to be data rather than a
constant: a trait, a spell or a level-up effect can raise it at runtime and the
whole clamp chain follows, because every reader asks `ceiling`. By default it
**does not change the current value** — a spell that lifts your maximum should
not silently heal you. Pass `"scale_current": true` to grant both. Lowering a
ceiling below the current value brings the value back under it rather than
leaving the vital above its own maximum.


## Baseline Decay

Every tick, `tick_turn()` applies baseline decay to all non-dead, non-slasher
characters through a single helper, `TickManager._decay(player, stat, amount,
minutes=...)`:

```python
rate = p.decay_rates.get(stat, BASELINE_DECAY.get(stat, 0.0))
mult = trait_multipliers.get(stat, 1.0)
self._decay(p, stat, -rate * mult)      # minutes defaults to tick_minutes(gs)
```

- **Rates are per in-game minute** and `_decay` scales them by the tick length, so
  the same numbers mean the same thing at 1 minute/tick and at 15. Sub-unit steps
  accumulate per character per vital, so a 0.0034/min drain still lands as whole
  points.
- **One helper** means every per-minute effect in the tick — baseline decay,
  condition periodics, activity regen, temperature drift — converts identically.
  Anything measuring time that does *not* go through it (or does not convert
  itself) is a bug waiting for someone to change the tick length; `npc_behaviors`
  intervals and the novelty recovery window were both exactly that.
- **Per-character override:** `decay_rates` on the player wins over the default.
  This is why a stale bake in a scenario can silently disable a mechanic — see
  `tests/test_decay_rate_bake.py` and task-431.
- Bladder is **not** in `BASELINE_DECAY` — it fills toward 100 separately (see
  [Bladder](#bladder--100-full)).

## Critical Vitals Effects

### HP = 0 → Death

When HP reaches 0, the character dies. The cause is read off the other vitals:

```python
cause_parts = []
if hunger >= 100: cause_parts.append("starvation")     # a DRIVE: fills up
if thirst >= 100: cause_parts.append("dehydration")     # a DRIVE: fills up
if temperature < cold_critical: cause_parts.append("hypothermia")
if temperature > heat_critical: cause_parts.append("heat stroke")
```

The temperature thresholds are **per species**, not the fixed 30/42 below —
`TraitSystem.get_temperature_band(player)` reads the character's temperature
band, so a creature with a different normal body temperature dies at its own
numbers. Sanity is deliberately absent; see below.

On death, everything routes through `world.kill_player` — see
[Which death path is authoritative](#which-death-path-is-authoritative-decided-task-538).

### Energy = 0 → Unconscious → Death

When Energy reaches 0:
1. Character becomes `"unconscious"` with `state_timer = 5`
2. Held items are dropped (you let go of what you were carrying)
3. Exhaustion count increments
4. On 3rd exhaustion: the character dies of "exposure"

### Hunger = 100, Thirst = 100

Hunger and Thirst are **drives** (task-337): they FILL toward 100, so starving
means *high* Hunger, not low. Maxed out for longer than a grace period they
cause HP damage, with cause "starvation" / "dehydration".

Grace and damage are counted in **game minutes**, so the grace period is the
same span of game time whatever the tick length. Thirsted grace is 60 minutes
(1 hour) and drains HP at 0.50/min; hunger's grace is 360 minutes (6 hours) and
drains at 0.10/min.

### Sanity = 0 does **not** damage HP

Being at 0 Sanity is deliberately **not** a death sentence, and this is easy to
get wrong: it is tempting to assume "every vital has a lethal zero", and Sanity
is the counter-example. It does not appear in the cause-of-death builder at
all, and it never drains HP. (An older revision of this page claimed a mad
character could be recorded as dying of "madness" — it cannot; the builder has
only ever listed starvation, dehydration, hypothermia and heat stroke.)

What low Sanity does instead is make the character **dangerous**. Below 25 it
applies the `paranoid` → `hallucinating` condition line, which carries
attack/defence modifiers rather than a health cost, mirroring `social_breakdown`
(task-353 §5).

**Sanity has sources** (task-432 — it used to have five drains and no inflow, so
every character went mad on a fixed schedule):

| Source | Rate | Where |
|---|---|---|
| Sleeping | +0.025/min | `activities.ACTIVITY_REGEN["sleeping"]` — the primary source |
| Resting | +0.05/min | `ACTIVITY_REGEN["resting"]` |
| Meditating | +0.05/min | `ACTIVITY_REGEN["meditating"]` |
| Company | +0.004/min while Social ≥ 70 | `tick_manager`, `SANITY_COMPANY_GAIN` — the mirror of the isolation penalty |

A night's sleep (~12 points) exceeds the passive daily drain (~7) but not by a
wide margin — deliberately, so rest matters and a character who is kept awake
slides. Background characters rest for `SANITY_REST_MINUTES` when Sanity is low
(see [Activities & States](Activities%20&%20States.md)).

### Bladder = 100 (Full)

Bladder is unique — it **fills** over time instead of decaying: 0 = empty
(relieved), 100 = full (need to go).

Fill rate is `BLADDER_FILL` (0.42/min), modulated by Thirst so a dehydrated body
conserves water. Crossing `BLADDER_THRESHOLD` (60) applies the Hygiene penalty
once; see `vital_rates.py`.

#### Relief: permitted anywhere, comfortable only in private (task-551)

**Any character can relieve themselves in any area.** There is deliberately no
check that refuses it. A world that happens to contain no latrine is not a world
where nobody can go — the `latrine` / `toilet` / `privy` / `restroom` /
`bathroom` tags mark a *proper place*, not the only legal one. Both tiers read
`engine/relief.py`, so a background goblin and a human at the keyboard get
identical rules.

What the tags buy is *comfort*, expressed as a dignity cost when relief happens
somewhere improvised:

| | Sanity | Social |
|---|---|---|
| In a proper place (area tag, or a fixture standing in the area) | — | — |
| Improvised, nobody watching | −2 | — |
| Improvised, at least one witness | −2 | −3 |

Being alone keeps it between you and the puddle, which is why the Social hit is
conditional. An improvised relief also writes `urine` into the area's
`environment.smell`; the foreground additionally spawns a `puddle` item, while
the background tier does not, so a hundred goblins improvising does not bury the
graph in scenery items.

Background characters *prefer* somewhere better. Every area within two ways
(`engine.relief.PRIVACY_SEARCH_HOPS`) is scored, lower being better:

```
score = 1.0 * (other characters in the area)
      − 1.5 * (area tagged private / secluded / isolated)
      − 1.0 * (a real relief fixture is here)
```

A character heads for the best score if it beats standing still, and relieves
where it is otherwise. Two details matter:

- **The occupancy term is the load-bearing one.** An author's `private` tag is a
  claim about a room; the number of people actually standing in one is what
  produced the traffic jam this replaced (in the Kraktooth camp the single
  `Waste Disposal` room was the only relief area out of 84 and the busiest room
  in the world). The tag is worth somewhat more than a single onlooker so a
  character will cross one room for a spot the author called secluded, but the
  hop budget — not the weight — is what stops it marching across a map.
- **At or above `RELIEF_URGENT` (90) the character relieves where it stands.**
  Below that it is willing to walk. The split is what stops a character
  oscillating between two equally mediocre rooms, and stops it dawdling while
  the involuntary threshold closes on it.

A tie is not worth a walk. An explicit `public` / `communal` tag overrules
`private` / `secluded` / `isolated`, so an author who bothered to say a great
hall is public meant it.

The weights are a parameter (`engine.relief.score_privacy(weights=...)`) so that
per-species and per-faction privacy is a one-argument change rather than a
redesign — that is task-549.

### Low Social / Low Entertainment

Both cause Sanity penalties (per minute):

- Social < 25: -0.005; < 50: -0.005 (`SANITY_PENALTY_SOCIAL_VERY_LOW` / `_LOW`)
- Entertainment < 25 / < 50: the same shape via `SANITY_PENALTY_ENT_*`

The mirror also exists: **company above 70 Social adds** `SANITY_COMPANY_GAIN`
rather than subtracting, so being connected steadies a character — but it is
smaller than the passive drain, so company alone is a steadying influence rather
than a source (task-432).

### Entertainment Is Paid by Novelty

Entertainment rises from **novelty** — a per-subject recovery curve, not the old
`visited_areas` / `discovered_items` sets (task-425):

```text
freshness = clamp((now - last_experienced) / recovery, 0, 1) ** 2
bonus     = round(NOVELTY_MAX * freshness)
```

- Subjects: **areas** (paid on arrival) and **items** (paid on first examination or
  take). A **person** is paid by `register_first_meeting`, not on sight — see below.
- `NOVELTY_MAX` 15, recovery window `entertainment.novelty_recovery_minutes`
  (default 120 game minutes), trait scaling `curious` ×1.5 / `homebody` 0 /
  `wanderlust` recovers on half the window.
- The curve is **squared** so a short gap is worth almost nothing: a two-room
  bounce pays nothing, which a linear ramp did not manage.
- A **daily budget** (`NOVELTY_DAILY_BUDGET` 30, below Entertainment's ~43/day
  decay) bounds it, because the window alone guards bouncing but not *roaming*: a
  character with 31 areas to visit sees a "fresh" one on every arrival.
- Recovery reads the subject's live observation memory (`Player.observation_tick`,
  task-403). **Absence of a memory means "never experienced"** and pays full.

**Authored sources are what hold the meter up**, not novelty: recreational
fixtures (`recreation`-tagged items with an authored `on_use → adjust_vital
Entertainment`) such as a drum, dice or a fire, plus `meditating`. A background
character seeks one when Entertainment drops to
`ENTERTAINMENT_THRESHOLD` (40).

Per-tick modifiers: `impatient` −3 when energetic, `patient` +1, `adventurous` +2
in unfamiliar areas, `no_entertainment_decay` (from `adventurous`) cancels decay.

## Vitals Need Messages

When a vital crosses a threshold (75→50, 50→25, 25→10), the active player receives a warning message (`tick_manager.py:67-84, 154-164`):

| Vital | 75 | 50 | 25 | 10 |
|-------|-----|-----|-----|-----|
| Energy | "getting a bit tired" | "quite weary" | "exhausted" | "barely stay awake" |
| Hunger | "stomach rumbling" | "quite hungry" | "famished" | "so hungry you feel weak" |
| Thirst | "bit parched" | "throat is dry" | "very thirsty" | "extremely dehydrated" |
| Hygiene | "not as fresh" | "grimy" | "quite dirty" | "clean up immediately" |
| Social | "bit lonely" | "miss people" | "isolated" | "desperately crave contact" |
| Bladder (fills ↑) | "bathroom soon" | "uncomfortably full" | "need a bathroom" | "serious discomfort" |
| Sanity | "bit unsettled" | "isolation getting to you" | "losing grip" | "barely hold it together" |
| Entertainment | "getting dull" | "need something to do" | "bored out of mind" | "monotony unbearable" |

## Environmental Effects on Vitals

Area environment properties affect vitals each tick (`tick_manager.py:184-260`):

| Condition | Effect |
|-----------|--------|
| Temperature > 30 | Thirst -2/tick (rapid) |
| Temperature > 40 | HP -1/tick |
| Temperature < 10 | Energy -1/tick |
| Temperature < 0 | HP -1/tick |
| Air = "stale" | Energy -1/tick |
| Air = "humid" | Social -1/tick |
| Air = "toxic" | HP -3/tick |
| Noise loud/dripping/scratches (while sleeping) | Energy -1/tick |
| Smell mold/rot/urine/etc | Hygiene -1/tick |
| Smell = "perfume" | Social +1/tick |
| Light < 20 | Sanity -1/tick |
| Other players in room | Social +1/tick |

### Temperature System

Body temperature drifts toward room temperature:
- Area < 15°C: body cools at `(15 - room) × 0.02` per tick, min 25°C
- Area > 30°C: body heats at `(room - 30) × 0.02` per tick, max 45°C
- Otherwise: drifts back toward 37°C at ±0.1/tick

(`tick_manager.py:232-244`)

Body temperature effects:
| Core Temp | Effects |
|-----------|---------|
| 35-37°C | Energy -1/tick |
| 33-35°C | Energy -2/tick, HP -1/tick |
| <33°C | HP -3/tick |
| 37-38°C | Thirst -1/tick |
| 38-40°C | HP -1/tick |
| >40°C | HP -3/tick |

(`tick_manager.py:246-259`)

## Vitals Restoration

### Rest / Sleep

Activities restore vitals through `activities.ACTIVITY_REGEN`, whose values are
**per game minute** and scaled by the tick length like every other rate:

| Activity | Restores |
|---|---|
| `sleeping` | Sanity +0.025/min; Energy handled by `tick_manager` (`SLEEP_ENERGY_REGEN`) |
| `resting` | Energy +0.15/min, Sanity +0.05/min |
| `meditating` | Sanity +0.05/min |
| `bathing` | Hygiene +1.5/min |
| `sitting` / `lying down` | Energy, slower than rest |

A sleeping character wakes when Energy is full, on damage, a loud noise (WIS save),
or when a duration elapses. **Wake-on-full-Energy is checked before the duration**,
so sleep cannot be used to rest at full Energy — that is why the background tier
uses a bounded *rest* to recover Sanity rather than sleep (task-432). See
[Activities & States](Activities%20&%20States.md) for the full activity model.

### Unconscious Recovery

While unconscious:
- Energy +4/tick (up to max 20)
- After 5 ticks: wakes up with Energy = 20

(`tick_manager.py:93-102`)

### Natural HP Regeneration

HP regenerates 1/tick (modified by traits) when ALL conditions are met:
- Energy > 25
- Hunger > 25
- Thirst > 25
- Sanity > 25
- Temperature 35-39°C
- **HP is below this character's maximum** (`ceiling(vitals, "HP")`, *not*
  the literal 100 — see [HP is on its own scale](#hp-is-on-its-own-scale-task-538))

Regen amount: `max(1, int(1 × hp_regen_multiplier))`. Default is 1, doubled by `fast_healer`, halved by `slow_healer`.

### Items

Items like food, water, medicine can restore vitals through triggers/effects. Items have `uses` and `action_costs` properties.

## Slasher Exemption

Characters with the `is_slasher` effect (from the `slasher` trait) are exempt from all vital decay and environmental effects (`tick_manager.py:104-106`). They are horror monsters that do not need to eat, sleep, or maintain hygiene.

## Death System

### Which death path is authoritative (decided, task-538)

**The `dead` condition is the single authoritative death state.**

`Player.state` is *derived* from the condition hierarchy
(`engine/player_conditions.get_state`, with `dead` at the top of
`CONDITION_HIERARCHY`), so `state == "dead"` and `has_condition("dead")` are the
same fact rather than two that can drift. Setting `player.state = "dead"` adds
the condition; it is not a second store. This answers the task's open question
of `p.state` vs the condition vs `HP <= 0` vs exhaustion count: they are not
four paths.

What was *not* settled was the causes. Four sites each set `state = "dead"`
and then did a different subset of the aftermath:

| Site | body | log | lived-log record | dropped held items |
|------|------|-----|------------------|--------------------|
| tick: `HP <= 0` | yes | yes | yes | **no** |
| tick: exhaustion ≥ 3 | yes | yes | **no** | (already dropped) |
| combat: `HP <= 0` | yes | yes | **no** | yes |
| `POST /api/players/<n>/kill` | yes | yes | **no** | **no** |

So a corpse's inventory survived a killing blow but not a script, and the lived
log — the record designed to explain *why* something happened — only ever saw
environmental deaths. They now all go through one function:

```python
world.kill_player(name, cause, *, drop_items=True, announce=True) -> bool
```

which zeroes HP, sets the condition, writes the `death` entry to the lived log
with `why="cause:death"`, drops held items, spawns the body, and announces.
It returns `False` for a character who was already dead, so a second lethal
check cannot spawn a second corpse. **Nothing should set `state = "dead"`
directly any more.**

### Causes of Death

1. **Combat**: HP reduced to 0 by attack damage
2. **Starvation**: HP depleted by maxed Hunger
3. **Dehydration**: HP depleted by maxed Thirst
4. **Hypothermia/Heat Stroke**: HP/Energy depleted by temperature extremes
5. **Exhaustion**: Energy = 0 three times
6. **Toxic air**: HP drained by toxic room air
7. **Allergic reaction**: HP drained by allergen (trait)
8. **`POST /api/players/<name>/kill`**: scripted

### On Death

Every one of the above does exactly this, via `world.kill_player`:

1. `player.vitals["HP"]` = 0
2. the `dead` condition is applied (so `player.state` reads `"dead"`)
3. held items fall to the floor
4. a body item is spawned via `spawn_body_item()` with the cause of death
5. a `death` entry is appended to the character's lived log (`why="cause:death"`)
6. if ghost mode is enabled, the dead player can continue acting
7. the active player sees "GAME OVER: You have died from \<cause\>"

Dead players are excluded from:
- Vital decay processing (`tick_manager.py:90-91`)
- Simple NPC processing (`npc_behaviors.py:35`)
- Player-in-room listings (when `include_ghosts=False`, `player_manager.py:183-185`)

## Vitals UI

Vitals are displayed in:
1. **Command output**: `stats()` command shows current vital values
2. **Inspector**: The character inspector shows all vitals as progress bars
3. **Need messages**: Automatic warnings when vitals cross thresholds
4. **Emotion system**: Low vitals influence emotion (e.g., low HP + damage = fear/anger)

## Vitals by Character Library Examples

Characters often start with vitals below 100 to simulate pre-existing conditions:

| Character | Energy | Hunger | Thirst | Hygiene | Sanity | Notes |
|-----------|--------|--------|--------|---------|--------|-------|
| Miki | 100 | 80 | 80 | 100 | — | Well-rested |
| Jake Halloway | 70 | 45 | 40 | 85 | 90 | Sleep-deprived, hungry |
| Kayla Jenkins | 100 | 80 | 80 | 100 | 100 | Fresh start |
| Kaelen Voss | 66 | 59 | 49 | 79 | 98 | Weary traveler, Temp 36.46°C |
| Sammy Lopez | 100 | 75 | 70 | 100 | 95 | Slightly on edge |
| Kyrie Johansen | 100 | 85 | 85 | 100 | 100 | Ready to go |

## Related tasks

- [[dev_tasks/review/characters/task-28-character_needs_system|task-28: Character needs system]]
- [[bug_5-rat-11-10-hp-with-low-hp-warning|bug-5: Rat 11/10 HP with low HP warning]]

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[sleep-rest|Sleep / rest]] (#11), [[vitals-needs|Vitals & needs]] (#16)

**Dev tasks** — [[dev_tasks/done/characters/task-28-character_needs_system|task]]

**Neighbouring notes** — [[Activities & States]], [[Background Simulation]], [[Character Images & Expression Packs]], [[Characters Overview]], [[Emotion & Affect System]], [[NPC Behavior System]]

<!-- connected:end -->
