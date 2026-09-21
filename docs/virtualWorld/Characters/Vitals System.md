# Vitals System

Vitals are numeric meters (0-100, except Temperature) that track a character's physical and mental state. They decay over time and must be maintained through actions like eating, drinking, resting, and socializing.

> **All rates on this page are per in-game MINUTE, not per tick.** The engine
> scales them by the tick's length (`world.time_per_tick_minutes`, see
> `vital_rates.tick_minutes`), so a 15-minute tick applies fifteen minutes of
> decay. The table below used to read "decay per tick" with whole numbers, from
> before the 2026-09 per-minute recalibration; a scenario that bakes rates in the
> old per-tick scale is caught by `tests/test_decay_rate_bake.py`.

## Vitals Reference

| Vital | Default | Min | Max | Decay/min | Critical at 0 |
|-------|---------|-----|-----|------------|----------------|
| `HP` | 100 | 0 | Max_HP | 0 (damage only) | Death |
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

(`vital_rates.BASELINE_DECAY` is the authority. From a full meter: Hunger reaches
the starvation edge in ~3 weeks, Thirst the dehydration edge in ~3 days, Energy
empties over a ~16h waking day, and Social/Hygiene/Entertainment run on a ~1-2 day
cycle.)

(`player.py:60-67`)

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

When HP reaches 0, the character dies. Cause of death is determined from other vitals:

```python
cause_parts = []
if hunger <= 0: cause_parts.append("starvation")
if thirst <= 0: cause_parts.append("dehydration")
if sanity <= 0: cause_parts.append("madness")
if temperature < 30: cause_parts.append("hypothermia")
if temperature > 42: cause_parts.append("heat stroke")
```

(`tick_manager.py:166-183`)

On death:
- State is set to `"dead"`
- A body item is spawned
- Ghost mode can be enabled to continue playing

### Energy = 0 → Unconscious → Death

When Energy reaches 0:
1. Character becomes `"unconscious"` with `state_timer = 5`
2. Exhaustion count increments
3. On 3rd exhaustion: character dies from "exposure" (`tick_manager.py:128-137`)

### Hunger = 0, Thirst = 0

Each causes HP damage:
- Hunger = 0: HP damage, cause "starvation"
- Thirst = 0: HP damage, cause "dehydration"

Starvation grace and damage are counted in **game minutes**, so the grace period
is the same span of game time whatever the tick length.

### Sanity = 0 does **not** damage HP

Being at 0 Sanity is deliberately **not** a death sentence, and this is easy to
get wrong from the code: `sanity <= 0` appears in the *cause of death* string
builder, so a character who happens to die while mad is recorded as having died of
"madness" — but Sanity never drains HP itself.

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
- HP < 100

(`tick_manager.py:272-277`)

Regen amount: `max(1, int(1 × hp_regen_multiplier))`. Default is 1, doubled by `fast_healer`, halved by `slow_healer`.

### Items

Items like food, water, medicine can restore vitals through triggers/effects. Items have `uses` and `action_costs` properties.

## Slasher Exemption

Characters with the `is_slasher` effect (from the `slasher` trait) are exempt from all vital decay and environmental effects (`tick_manager.py:104-106`). They are horror monsters that do not need to eat, sleep, or maintain hygiene.

## Death System

### Causes of Death

1. **Combat**: HP reduced to 0 by attack damage
2. **Starvation**: HP depleted by hunger = 0
3. **Dehydration**: HP depleted by thirst = 0
4. **Madness**: HP depleted by sanity = 0
5. **Hypothermia/Heat Stroke**: HP/Energy depleted by temperature extremes
6. **Exhaustion**: Energy = 0 three times
7. **Toxic air**: HP drained by toxic room air
8. **Allergic reaction**: HP drained by allergen (trait)

### On Death

1. `player.vitals["HP"]` = 0
2. `player.state` = "dead"
3. A body item is spawned via `spawn_body_item()` with cause of death
4. If ghost mode is enabled, the dead player can continue acting
5. The active player sees "GAME OVER: You have died from <cause>"

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
- [[bug_5-rat-11-10-hp-with-low-hp-warning 1|bug-5: Rat 11/10 HP with low HP warning]]
