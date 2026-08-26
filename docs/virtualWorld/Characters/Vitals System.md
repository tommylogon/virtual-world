# Vitals System

Vitals are numeric meters (0-100, except Temperature) that track a character's physical and mental state. They decay over time and must be maintained through actions like eating, drinking, resting, and socializing.

## Vitals Reference

| Vital | Default | Min | Max | Decay/Tick | Critical at 0 |
|-------|---------|-----|-----|------------|----------------|
| `HP` | 100 | 0 | Max_HP | 0 (damage only) | Death |
| `Max_HP` | 100 | — | — | — | — |
| `Energy` | 100 | 0 | 100 | 1 | Unconscious → Death (after 3x) |
| `Hunger` | 100 | 0 | 100 | 1 | HP -1/tick |
| `Thirst` | 100 | 0 | 100 | 1 | HP -2/tick |
| `Hygiene` | 100 | 0 | 100 | 1 | — |
| `Social` | 100 | 0 | 100 | 1 | Sanity penalty |
| `Bladder` | 0 | 0 | 100 | — (fills +1/tick) | Hygiene -30 when hitting 100 |
| `Sanity` | 100 | 0 | 100 | 1 | HP -1/tick |
| `Entertainment` | 100 | 0 | 100 | 1 | Sanity penalty |
| `Temperature` | 37.0 | ~25 | ~45 | — | HP/Energy damage at extremes |

(`player.py:60-67`)

## Baseline Decay

Every tick, `tick_turn()` (`tick_manager.py:64-318`) applies baseline decay to all non-dead, non-slasher characters:

```python
for stat, default_decay in self.player_manager.baseline_decay.items():
    if stat in p.vitals and stat != "Temperature":
        rate = p.decay_rates.get(stat, default_decay)
        mult = trait_multipliers.get(stat, 1.0)
        p.vitals[stat] = max(0, p.vitals[stat] - int(rate * mult))
```

Bladder is **not** in `baseline_decay` — it fills toward 100 separately (see [Bladder = 100](#bladder--100-full)).

Each stat decays by its `decay_rate × vital_multiplier` per tick. Bladder is the exception — it fills instead of decays (see below). Characters can override decay rates per-stat via `decay_rates` (`player.py:69-73`).

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

### Hungry = 0, Thirst = 0, Sanity = 0

Each causes HP damage per tick:
- Hunger = 0: -1 HP/tick
- Thirst = 0: -2 HP/tick
- Sanity = 0: -1 HP/tick

(`tick_manager.py:141-149`)

### Bladder = 100 (Full)

Bladder is unique — it **fills** over time instead of decaying: 0 = empty (relieved), 100 = full (need to go). On the tick it first hits 100, it triggers a -30 Hygiene penalty (`tick_manager.py:161-162`).

Fill rate is influenced by Thirst:
- Thirst &gt; 75 (well hydrated): +2/tick
- Thirst 25–75: +1/tick (normal)
- Thirst &lt; 25 (dehydrated): +0/tick (body conserves water)

### Low Social / Low Entertainment

Both cause Sanity penalties:
- Social < 25: -2 Sanity/tick; < 50: -1 Sanity/tick
- Entertainment < 25: -2 Sanity/tick; < 50: -1 Sanity/tick

(`tick_manager.py:221-231`)

### Entertainment Gains (novelty, task-136)

Entertainment rises naturally from novelty, tracked per character via `visited_areas` and `discovered_items` sets:

| Source | Base boost | Where |
|--------|-----------|-------|
| First visit to an area | +15 | `movement.py:226-240` |
| First discovery of an item (examine/take) | +8 | `item_actions.py:_register_item_discovery` |
| First meeting a new character | +10 | `player.py:register_first_meeting` / `update_relationship` |

Trait modifiers: `curious` ×1.5, `homebody` 0. All boosts clamp at 100. Repeated visits/discoveries/meetings give nothing (set-based diminishing returns). Per-tick modifiers: `impatient` −3 when energetic, `patient` +1, `adventurous` +2 in unfamiliar areas, `no_entertainment_decay` (from `adventurous`) cancels decay (`tick_manager.py:127-143`).

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

The `rest()` command (`tick_manager.py:325-341`):
1. Sets player state to "sleeping" for N ticks
2. Each sleeping tick: Energy +3 (`tick_manager.py:261-262`)
3. Awakens after the rest period
4. Returns energy restored and current energy

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
